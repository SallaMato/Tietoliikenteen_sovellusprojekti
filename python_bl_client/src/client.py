'''
Ohjelma yhdistää bluetooth laitteeseen. 

Ohjelma käyttää ".env" -tiedostoa, jonne pitää laittaa muuttujat
DEVICE_ADDR=""
CHARACTERISTIC_UUID=""
PACKET_DATA_LEN_BYTES="241"
TIMER_SECONDS="10"

HUOM! Paketin rakenne täytyy olla:
1. Tavu = Suunta
Tämän jälkeen X, Y, Z arvot joista jokainen 16bit.

Alustus (tarvitsee tehdä vain kerran):
1: Kannattaa ensin tehdä "python_bl_client" kansiossa python environment komennolla:
   python -m venv .venv

2: Aiempi komento luo ".venv/Scripts" kansion. Aja sieltä "activate.bat" -komento.
   Tämä aktivoi python environmentin. Tiedät että olet environmentissa kun komentokehotteeseen tulee
   "(.venv)" etuliite. Nyt kaikki moduuliasennukset (pip install <module>) asentuvat vain tälle
   environmentille paikallisesti.
  
3: Kokeile ajaa "client.py". Todennäköisesti saat virheen "ModuleNotFoundError: No module named 'bleak'".
   Voit asentaa sen "pip install bleak" -komennolla. Toista sama mahdollisten muiden puuttuvien moduuleiden
   kohdalla.

Esimerkki ohjelman ajamisesta:
1: Varmista että olet aktivoinut environmentin, eli aja komento "Scripts/activate.bat".

2: Aja komento "python client.py <laitteen osoite> <UUID>
   Esim: python client.py "DE:8D:ED:BD:1A:D0" "00001526-1212-efde-1523-785feabcd123"

   Jos et tiedä laitteen osoitetta, aja scanner.py scripti. Se skannaa laitteita
   ja printtaa listan niistä. Etsi oma laite listasta, näet listassa laitteen osoitteen.
   Voit tämän jälkeen ajaa client.py scriptin uudestaan osoitteellasi.

   Jos et tiedä characteristic UUID numeroa, client.py printtaa listan kaikista
   characteristiceista. Kopioi haluttu UUID ja aja ohjelma osoitteen ja UUID:n kanssa uudestaan.
'''

from nt import rename
import os
import struct
import csv
import time
import asyncio
from bleak import BleakClient
from dotenv import load_dotenv

# Ladataan ympäristömuuttujat .env tiedostosta.
load_dotenv()

# Avataan valmiiksi csv tiedosto, jotta kirjoittaminen olisi (toivottavasti) nopeampaa.
os.makedirs("../data/temp", exist_ok=True)
file = open('../data/temp/data.csv', 'w', newline='')
writer = csv.writer(file)

# Haetaan .env tiedostosta muuttujat.
addr = os.getenv("DEVICE_ADDR")
uuid = os.getenv("CHARACTERISTIC_UUID")
packet_data_len_bytes = int(os.getenv("PACKET_DATA_LEN_BYTES"))
timer_seconds = int(os.getenv("TIMER_SECONDS"))

label0 =  os.getenv("LABEL_0")
label1 =  os.getenv("LABEL_1")
label2 =  os.getenv("LABEL_2")
label3 =  os.getenv("LABEL_3")
label4 =  os.getenv("LABEL_4")
label5 =  os.getenv("LABEL_5")

# Map suunta --> label
labels = {"0": label0, "1": label1, "2": label2, "3": label3, "4": label4, "5": label5}

stop_event = asyncio.Event()
packet_count = 0
shutdown_requested = False
timer_started = False
suunta = None

def request_shutdown():
    global shutdown_requested
    shutdown_requested = True
    print(f"{timer_seconds}s elapsed. Stopping capture...")
    stop_event.set()

def process_data(buffer):
    global packet_count
    global shutdown_requested
    global timer_started
    global suunta
    
    if shutdown_requested:
        return

    # Start timer when first packet arrives
    if not timer_started:
        timer_started = True
        loop = asyncio.get_running_loop()
        loop.call_later(timer_seconds, request_shutdown)

    packet_count += 1     
    suunta = buffer[0]
    print(f"----- Packet {packet_count} -----")
    for i in range ((packet_data_len_bytes - 1) // 6):
        measurement = struct.unpack_from('HHH', buffer, 1+i*6)
        writer.writerows([[str(measurement[0]), str(measurement[1]), str(measurement[2])]])
        print(f"suunta: {suunta}, x: {measurement[0]}, y: {measurement[1]}, z: {measurement[2]}")
    print("----------\n")
    
def notification_handler(sender, data):
    process_data(data)

async def main():
    async with BleakClient(addr) as client:
        # Hakee kaikki laitteen servicet ja characteristicit ja tulostaa ne.
        for service in client.services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"Characteristic: {char.uuid}, properties={char.properties}")

        # Jos uuid:ta ei ole annettu, lopetetaan ohjelma
        if not uuid:
            print("uuid not given, exiting...")
            return

        # Kirjoitetaan csv tiedostolle otsikot
        writer.writerows([["x", "y", "z"]])

        # Tilataan notifikaatiot ja odotetaan
        try:
            print(f"Starting notifications. Timer ({timer_seconds}s) will start after receiving first packet.")
            await client.start_notify(uuid, notification_handler)
            await stop_event.wait()
        finally:
            print("Stopping notifications...")
            await client.stop_notify(uuid)
            file.flush()
            file.close()
            # Luodaan tiedosto lopullista sample tiedostoa varten
            os.makedirs(f"../data/{suunta}", exist_ok=True)
            os.rename("../data/temp/data.csv", f"../data/{suunta}/data_{suunta}_{timer_seconds}_{int(time.time())}.csv")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Interrupted")
finally:
    # Suljetaan csv tiedosto
    file.close()
    print("Exiting...")
