'''
Ohjelma yhdistää bluetooth laitteeseen jonka osoite on
addr (argv[1]) ja tilaa characteristicin jonka uuid on
char_uuid (argv[2]). Vastaanotettu data tallennetaan .csv tiedostoon.

cmdline argumenttien sijaan voidaan myös käyttää ".env" -tiedostoa, jonne pitää laittaa muuttujat
DEVICE_ADDR=""
CHARACTERISTIC_UUID=""

HUOM! datan pitää olla joko 8 tavuinen byte array (suunta, x, y, z), tai 6 tavuinen byte array (x, y, z)

Alustus (tarvitsee tehdä vain kerran):
1: Kannattaa ensin tehdä python environment komennolla:
   python -m venv /path/to/new/virtual/environment   <-- muokkaa tiedostopolku osoittamaan "python_bl_client" -kansioon

2: Aiempi komento luo "Scripts" kansion. Aja komentokehotteella "Scripts" kansiossa "activate.bat" -komento.
   Tämä aktivoi python environmentin. Tiedät että olet environmentissa kun komentokehotteeseen tulee
   "(python_bl_client)" etuliite. Nyt kaikki moduuliasennukset (pip install <module>) asentuvat vain tälle
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

import sys
import os
import numpy as np
import struct
import csv
import asyncio
from bleak import BleakClient
from dotenv import load_dotenv

# Ladataan ympäristömuuttujat .env tiedostosta.
load_dotenv()

# Avataan valmiiksi csv tiedosto, jotta kirjoittaminen olisi (toivottavasti) nopeampaa.
file = open('data.csv', 'w', newline='')
writer = csv.writer(file)

# Haetaan .env tiedostosta muuttujat. Nämä voidaan ylikirjoittaa cmdline argumenteilla.
addr = os.getenv("DEVICE_ADDR")
uuid = os.getenv("CHARACTERISTIC_UUID")
packet_data_len_bytes = int(os.getenv("PACKET_DATA_LEN_BYTES"))
measurement_len = int(os.getenv("MEASUREMENT_LEN_BYTES"))


# Prosessoidaan cmdline argumentit.
if len(sys.argv) == 3:
    addr = sys.argv[1]
    uuid = sys.argv[2]
elif len(sys.argv) == 2:
    addr = sys.argv[1]
    uuid = ""
elif addr is None or addr == "":
    print("Usage: client.py <address> [OPTIONAL]: <uuid>")
    print("Alternative: use a .env file with DEVICE_ADDR and CHARACTERISTIC_UUID variables")
    exit(1)

# X, Y, Z
def process_data1(data):
    measurement = struct.unpack('HHHH', data)
    print(f"x: {measurement[0]}, y: {measurement[1]}, z: {measurement[2]}")

    # Kirjoitetaan arvot csv tiedostoon. flush = pakottaa kirjoitetut arvot tallentumaan levylle asti heti
    # TODO: Kannattaako flushia tehdä joka arvon kohdalla? Pitäisikö tehdä batcheittain????
    writer.writerows([[str(measurement[0]), str(measurement[1]), str(measurement[2])]])
    file.flush()
    
# Suunta, X, Y, Z
def process_data2(data):
    measurement = struct.unpack('HHHH', data)
    print(f"Suunta: {measurement[0]}, x: {measurement[1]}, y: {measurement[2]}, z: {measurement[3]}")

    # Kirjoitetaan arvot csv tiedostoon. flush = pakottaa kirjoitetut arvot tallentumaan levylle asti heti
    # TODO: Kannattaako flushia tehdä joka arvon kohdalla? Pitäisikö tehdä batcheittain????
    writer.writerows([[str(measurement[0]), str(measurement[1]), str(measurement[2]), str(measurement[3])]])
    file.flush()

def process_data(buffer):
    suunta = struct.unpack('H', buffer)
    for i in range ((packet_data_len_bytes - 1)//measurement_len):
        measurement = struct.unpack('HHH', buffer[1+i*measurement_len])
        print(f"suunta: {suunta}, x: {measurement[0]}, y: {measurement[1]}, z: {measurement[2]}")
        writer.writerows([[str(measurement[0]), str(measurement[1]), str(measurement[2])]])
        file.flush()
    
def notification_handler(sender, data):
    # print(f"Notification from {sender}: {data.hex()}")
    # print("Data type:", type(data))
    # print("Data len:", len(data))
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
        if measurement_len == 8:
            writer.writerows([["suunta", "x", "y", "z"]])
        elif measurement_len == 6:
            writer.writerows([["x", "y", "z"]])

        # Tilataan notifikaatiot ja odotetaan ikuisuus (.Future), kunnes tulee KeyboardInterrupt
        try:
            await client.start_notify(uuid, notification_handler)
            print("Notifications enabled. Press Ctrl+C to quit.")
            await asyncio.Future()
        finally:
            print("Stopping notifications...")
            await client.stop_notify(uuid)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    # Suljetaan csv tiedosto
    file.close()
    print("Exiting...")
