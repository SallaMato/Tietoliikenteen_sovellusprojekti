'''
Ohjelma yhdistää bluetooth laitteeseen, tilaa kiihtyvyysanturidata notifikaatiot,
ja tallentaa samplet tiedostoihin. Ohjelma tallentaa sampleja kunnes MAX_SAMPLE_COUNT
on saavutettu. Ohjelma rakentaa "data" alikansion "python_bl_client" kansioon, jonne se tekee omat kansiot jokaiselle
suunnalle. 
'''

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
max_sample_count = int(os.getenv("MAX_SAMPLE_COUNT"))

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
sample_count = 0
shutdown_requested = False
suunta = None

def request_shutdown():
    global shutdown_requested
    shutdown_requested = True
    print(f"{sample_count} samples captured. Stopping capture...")
    stop_event.set()

def process_data(buffer):
    global packet_count
    global sample_count
    global shutdown_requested
    global timer_started
    global suunta
    
    if shutdown_requested:
        return

    packet_count += 1     
    suunta = buffer[0]
    print(f"----- Packet {packet_count} -----")
    for i in range ((packet_data_len_bytes - 1) // 6):
        if sample_count < max_sample_count:
            measurement = struct.unpack_from('HHH', buffer, 1+i*6)
            writer.writerows([[str(measurement[0]), str(measurement[1]), str(measurement[2])]])
            print(f"suunta: {suunta}, x: {measurement[0]}, y: {measurement[1]}, z: {measurement[2]}")

        sample_count += 1
        if sample_count == max_sample_count:
            request_shutdown()
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
            print(f"Starting notifications until {max_sample_count} samples have been captured.")
            await client.start_notify(uuid, notification_handler)
            await stop_event.wait()
        finally:
            print("Stopping notifications...")
            await client.stop_notify(uuid)
            file.flush()
            file.close()
            # Luodaan tiedosto lopullista sample tiedostoa varten
            os.makedirs(f"../data/{suunta}", exist_ok=True)
            os.rename("../data/temp/data.csv", f"../data/{suunta}/data_{suunta}_S{max_sample_count}_{int(time.time())}.csv")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Interrupted")
finally:
    # Suljetaan csv tiedosto
    file.close()
    print("Exiting...")
