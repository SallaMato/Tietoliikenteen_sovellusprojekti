import os
import struct
import asyncio
from bleak import BleakClient
from dotenv import load_dotenv
from mysql.connector.aio import connect

# Ladataan ympäristömuuttujat .env tiedostosta.
load_dotenv()

# Haetaan .env tiedostosta muuttujat.
addr = os.getenv("DEVICE_ADDR")
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
queue = asyncio.Queue()

# Säikeiden lukumäärä, jotka prosessoivat datan kirjoitusta SQL tietokantaan
num_worker_threads = 3

# Tähän muuttujaan laitetaan SQL prosessointisäikeet
worker_threads = []

packet_count = 0
sample_count = 0
shutdown_requested = False
suunta = None

# MySQL yhteyden asetukset
config = {
    "host": mysql_addr,
    "port": mysql_port,
    "user": mysql_user,
    "password": mysql_pass,
    "use_pure": True,
    "autocommit": False
}

def request_shutdown():
    global shutdown_requested
    shutdown_requested = True
    stop_event.set()

    
# -------------------
# SQL PROSESSOINTI
# -------------------
async def insert_into_rawdata(groupid, from_mac, to_mac,
                               sensorvalue_a, sensorvalue_b,
                               sensorvalue_c, sensorvalue_d,
                               sensorvalue_e, sensorvalue_f,
                               cnx, cur):
    stmt = """
    INSERT INTO measurements.rawdata (
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

async def queue_handler(thread_id, queue, cnx, cur):
    print(f"running thread {thread_id}")
    global packet_count
    global sample_count
    global shutdown_requested
    global suunta
    
    while True:
        # Hae queuessa olevan objektin parametrit (ne jotka annoimme kun kutsuimme queue.put funktiota)
        sender, buffer = await queue.get()
        print("sender:", sender)
        print("buffer:", buffer)

        packet_count += 1

        # Jokaisen BLE paketin ensimmäinen tavu sisältää suunnan
        suunta = buffer[0]

        for i in range ((packet_data_len_bytes - 1) // 6):
            if sample_count < max_sample_count:
                measurement = struct.unpack_from('HHH', buffer, 1+i*6)
                res = await insert_into_rawdata(
                    "666",
                    "AA:BB:CC:DD:EE:FF",
                    "11:22:33:44:55:66",
                    str(measurement[0]),
                    str(measurement[1]),
                    str(measurement[2]),
                    "0",
                    "0",
                    "testi_data_sensori",
                    cnx, cur)

            sample_count += 1
            if sample_count == max_sample_count:
                request_shutdown()
                
        await cnx.commit()

        # Kerrotaan queuelle, että taski on valmis
        queue.task_done()

async def job_mysql():
    try:
        # Avataan niin monta SQL yhteyttä kuin meillä on säikeitä
        aws = [connect(**config) for _ in range(num_worker_threads)]
        cnxs = [await coro for coro in asyncio.as_completed(aws)]
        
        aws = [cnx.cursor() for cnx in cnxs]
        curs = [await coro for coro in asyncio.as_completed(aws)]

        for i in range(num_worker_threads):
            # Create worker  threads to handle the queue
            worker_thread = asyncio.create_task(queue_handler(i, queue, cnxs[i], curs[i]))
            worker_threads.append(worker_thread)

        # Wait for the stop event before releasing mysql and queue resources
        await stop_event.wait()

    finally:
        # Wait until the queue is fully processed.
        await queue.join()

        # Cancel worker threads
        for i in range(len(worker_threads)):
            print(f"Cancelling thread {i}")
            worker_threads[i].cancel()
        
        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*worker_threads, return_exceptions=True)

# -------------------
# BLE PROCESSING
# -------------------
def notification_handler(sender, data):
    if shutdown_requested:
        return

    # Post work to the queue, will block if queue is full. NOTE: put_nowait would not block, but is it safe??
    queue.put((sender, data))
    
async def job_ble():
    # TEST: Rakennetaan dummy BLE paketteja ja lähetetään queuelle
    
    global packet_data_len_bytes
    packet_data_len_bytes = 9
    for i in range(10):
        test_data = struct.pack('<BHHH', 1, 2000, 3000, 4000)
        await queue.put((f"lahettaja_{i}", test_data))
    return
    
    #  TESTI LOPPU
    
    async with BleakClient(addr) as client:
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
