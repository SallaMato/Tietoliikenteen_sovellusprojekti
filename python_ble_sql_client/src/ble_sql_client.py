'''
Ohjelma yhdistää bluetooth laitteeseen, tilaa kiihtyvyysanturidata notifikaatiot,
ja tallentaa samplet mySQL tietokantaan. Ohjelma tallentaa sampleja kunnes MAX_SAMPLE_COUNT
on saavutettu.

HUOM! Testattu: nordic lähettää dataa -->  prosessoidaan 10 samplea ja kirjoitetaan paikalliseen tietokantaan
      EI vielä testattu raspberryn kanssa, eikä ubuntu tietokantojen kanssa, ainoastaan läppärillä paikalliseen tietokantaan.

TODO: Kirjoita data tietokantaan isommissa batcheissa.
'''

import os
import struct
import asyncio
from bleak import BleakClient
from dotenv import load_dotenv
from mysql.connector.aio import connect

# Ladataan ympäristömuuttujat .env tiedostosta.
load_dotenv()

# Haetaan .env tiedostosta muuttujat.
device_addr = os.getenv("DEVICE_ADDR")
uuid = os.getenv("CHARACTERISTIC_UUID")
packet_data_len_bytes = int(os.getenv("PACKET_DATA_LEN_BYTES"))
max_sample_count = int(os.getenv("MAX_SAMPLE_COUNT"))

mysql_addr= os.getenv("MYSQL_ADDR")
mysql_port= int(os.getenv("MYSQL_PORT"))
mysql_user= os.getenv("MYSQL_USER")
mysql_pass= os.getenv("MYSQL_PASS")
mysql_db_name = os.getenv("MYSQL_DB_NAME")

# Event, joka pysäyttää ohjelman
stop_event = asyncio.Event()

# Jono, johon BLE paketit laitetaan prosessoitavaksi
queue_max_size = 1000
queue = asyncio.Queue(maxsize=queue_max_size)

# Tällä lukolla varmistetaan, että sample_count muuttujaa lukee yksi säie kerrallaan
sample_count_lock = asyncio.Lock()

# Säikeiden lukumäärä, jotka prosessoivat datan kirjoitusta SQL tietokantaan
num_worker_threads = 3

# Tähän muuttujaan laitetaan SQL prosessointisäikeet
worker_threads = []

packet_count = 0
sample_count = 0
shutdown_requested = False

# MySQL yhteyden asetukset
config = {
    "host": mysql_addr,
    "port": mysql_port,
    "user": mysql_user,
    "password": mysql_pass,
    "database": mysql_db_name,
    "use_pure": True,
    "autocommit": False
}

def request_shutdown():
    global shutdown_requested
    shutdown_requested = True
    stop_event.set()

    
# -------------------
# SQL
# -------------------
async def insert_into_rawdata(groupid, from_mac, to_mac,
                               sensorvalue_a, sensorvalue_b,
                               sensorvalue_c, sensorvalue_d,
                               sensorvalue_e, sensorvalue_f,
                               cnx, cur):
    stmt = """
    INSERT INTO rawdata (
        groupid,
        from_mac,
        to_mac,
        sensorvalue_a,
        sensorvalue_b,
        sensorvalue_c,
        sensorvalue_d,
        sensorvalue_e,
        sensorvalue_f
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    await cur.execute(stmt,
        (
            groupid,
            from_mac,
            to_mac,
            sensorvalue_a,
            sensorvalue_b,
            sensorvalue_c,
            sensorvalue_d,
            sensorvalue_e,
            sensorvalue_f
        )
    )

# Estetään mahdollinen race condition ja lisätään sample_count muuttujaan 1
async def increment_sample_count() -> bool:
    global sample_count
    async with sample_count_lock:
        if sample_count >= max_sample_count:
            return False
        sample_count += 1
        return True

async def queue_handler(thread_id, queue, cnx, cur):
    print(f"worker {thread_id} started")
    global packet_count
    global sample_count
    global shutdown_requested
    global device_addr
    global sample_count_lock
    
    while True:
        # Hae queuessa olevan objektin parametrit (ne jotka annoimme kun kutsuimme queue.put funktiota)
        buffer = await queue.get()

        try:
            # Tätä ei käytetä tällä hetkellä mihinkän hyödylliseen, joten ei tarvitse suojata lockilla.
            packet_count += 1

            # Jokaisen BLE paketin ensimmäinen tavu sisältää suunnan
            suunta = buffer[0]

            for i in range ((packet_data_len_bytes - 1) // 6):
                if not await increment_sample_count():
                    request_shutdown()
                    break

                measurement = struct.unpack_from('<HHH', buffer, 1+i*6)
                print(f"[sql]: device: {device_addr}, suunta: {suunta}, x: {measurement[0]}, y: {measurement[1]}, z: {measurement[2]}")

                # TODO: Placeholder table, pitää muokata omaan käyttöön sopivaksi
                res = await insert_into_rawdata(
                    "0",
                    device_addr,
                    "11:22:33:44:55:66", # Tähän pitäisi jotenkin saada tämän laitteen BLE osoite....miten?? TODO: ota selvää
                    measurement[0],
                    measurement[1],
                    measurement[2],
                    0,
                    0,
                    suunta,
                    cnx, cur)

            # Kirjoitetaan rivit databaseen
            await cnx.commit()
            
        except Exception:
            # Virheen sattuessa rollback ja keskeytetään
            await cnx.rollback()
            raise
        finally:
            # Kerrotaan queuelle, että taski on valmis
            queue.task_done()

async def job_mysql():
    cnxs = []
    curs = []
    try:
        # Avataan niin monta SQL yhteyttä kuin meillä on säikeitä
        cnxs = await asyncio.gather(*[connect(**config) for _ in range(num_worker_threads)])
        curs = await asyncio.gather(*[cnx.cursor() for cnx in cnxs])

        for i in range(num_worker_threads):
            # Luodaan säikeitä queuen käsittelyä varten
            worker_thread = asyncio.create_task(queue_handler(i, queue, cnxs[i], curs[i]))
            worker_threads.append(worker_thread)

        # Odotetaan stop signaalia, ennen SQL resurssien vapauttamista
        await stop_event.wait()

    finally:
        # Odotetaan kunnes queue on kokonaan prosessoitu
        await queue.join()

        # Pysäytetään säikeet
        for i in range(len(worker_threads)):
            print(f"[sql]: Cancelling thread {i}")
            worker_threads[i].cancel()
        
        # Odotetaan kunnes säikeet ovat pysähtyneet
        await asyncio.gather(*worker_threads, return_exceptions=True)

        # Suljetaan SQL yhteydet
        for cur in curs:
            await cur.close()
        for cnx in cnxs:
            await cnx.close()

# -------------------
# BLE
# -------------------
async def notification_handler(sender, data):
    if shutdown_requested:
        return

    if len(data) != packet_data_len_bytes:
        print("Unexpected packet size")
        return

    # Lähetä paketit käsiteltäväksi queueen. Jos jono täysi, tiputa paketti
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        print("Queue full! Packet dropped.")
    
async def job_ble():
    # TEST: Rakennetaan dummy BLE paketteja ja lähetetään queuelle
    '''
    global packet_data_len_bytes
    packet_data_len_bytes = 9
    for i in range(10):
        test_data = struct.pack('<BHHH', 1, 2000, 3000, 4000)
        await queue.put((f"lahettaja_{i}", test_data))
    return
    '''
    #  TESTI LOPPU
    
    async with BleakClient(device_addr) as client:
        # Hakee kaikki laitteen servicet ja characteristicit ja tulostaa ne.
        for service in client.services:
            print(f"[ble]:Service: {service.uuid}")
            for char in service.characteristics:
                print(f"[ble]:Characteristic: {char.uuid}, properties={char.properties}")

        # Jos uuid:ta ei ole annettu, lopetetaan ohjelma
        if not uuid:
            print("[ble]:uuid not given, exiting...")
            return

        # Tilataan notifikaatiot ja odotetaan
        try:
            print(f"[ble]: Starting notifications until {max_sample_count} samples have been captured.")
            await client.start_notify(uuid, notification_handler)
            await stop_event.wait()
        finally:
            print("[ble]: Stopping notifications...")
            await client.stop_notify(uuid)

# -------------------
# MAIN
# -------------------
async def main_asynchronous():
    aws = (job_ble(), job_mysql())
    returned_vals = await asyncio.gather(*aws)

try:
    asyncio.run(main_asynchronous())
except KeyboardInterrupt:
    print("Interrupted")
finally:
    print("Exiting...")
