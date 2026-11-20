'''
Ohjelma yhdistää bluetooth laitteeseen, tilaa kiihtyvyysanturidata notifikaatiot,
ja tallentaa samplet tiedostoihin. Ohjelma tallentaa sampleja kunnes MAX_SAMPLE_COUNT
on saavutettu. Ohjelma rakentaa "data" alikansion "python_ble_binary_client" kansioon,
jonne se tekee alikansion joka nimetään "LABEL" .env muuttujan mukaan. Tiedot tallennetaan
.npy muotoon. 
'''

import os
import time
import math
import numpy as np
import struct
import asyncio
import logging
from bleak import BleakClient
from dotenv import load_dotenv

# Logging. Kehitysvaiheessa DEBUG, lopuksi vaihdetaan ERROR
logging.basicConfig(level=logging.DEBUG)

# Ladataan ympäristömuuttujat .env tiedostosta.
load_dotenv()

# Haetaan .env tiedostosta muuttujat.
addr = os.getenv("DEVICE_ADDR")
uuid = os.getenv("CHARACTERISTIC_UUID")
packet_data_len_bytes = int(os.getenv("PACKET_DATA_LEN_BYTES"))
max_sample_count = int(os.getenv("MAX_SAMPLE_COUNT"))
label = os.getenv("LABEL")

samples_per_packet = (packet_data_len_bytes - 1) // 6
num_packets_to_capture = math.ceil(max_sample_count / samples_per_packet)

# Kerätään paketit taulukkoon
packets = np.zeros((num_packets_to_capture, packet_data_len_bytes), dtype=np.uint8)

stop_event = asyncio.Event()
packet_count = 0
shutdown_requested = False

# For debugging
last_time = None

def request_shutdown():
    global shutdown_requested
    shutdown_requested = True
    stop_event.set()

def process_captured_packets():
    # Tehdään kansio dataa varten, jos sitä ei ole jo olemassa
    os.makedirs(f"../data/{label}", exist_ok=True)

    # Formatoidaan tiedostonimi
    filename = f"../data/{label}/data_{label}_S{max_sample_count}_{int(time.time())}.npy"

    # Sample laskuri
    sample_count = 0

    # Avataan tiedosto binary kirjoitusta varten, ja kirjoitetaan x,y,z samplet tiedostoon
    with open(filename, 'wb') as f:
        for packet in packets:
            suunta = packet[0] # Jokaisen paketin 1. tavu sisältää suunnan, tarvitaanko??
            for i in range (samples_per_packet):
                measurement = struct.unpack_from('HHH', packet, 1+i*6)
                # logging.debug(f"suunta: {suunta}, x: {measurement[0]}, y: {measurement[1]}, z: {measurement[2]}")
                np.save(f, measurement)
                sample_count += 1
                if(sample_count >= max_sample_count):
                    logging.info(f"{sample_count} samples saved to file.")
                    return


def notification_handler(sender, data):
    global packet_count
    global last_time
    
    if packet_count >= num_packets_to_capture:
        if shutdown_requested == False:
            request_shutdown()
        return

    if len(data) != packet_data_len_bytes:
        logging.warning("Unexpected packet size")
        return
    
    packets[packet_count] = data
    packet_count += 1

    if packet_count % 50 == 0:
        logging.info(f"packet_count: {packet_count}")
        now = time.perf_counter()
        if last_time is not None:
            dt = now - last_time
            logging.info(f"50 packets took {dt:.3f}s " f"({50/dt:.1f} packets/s)")
        last_time = now

async def main():
    async with BleakClient(addr) as client:
        # Hakee kaikki laitteen servicet ja characteristicit ja tulostaa ne.
        for service in client.services:
            logging.debug(f"Service: {service.uuid}")
            for char in service.characteristics:
                logging.info(f"Characteristic: {char.uuid}, properties={char.properties}")

        # Jos uuid:ta ei ole annettu, lopetetaan ohjelma
        if not uuid:
            logging.error("uuid not given, exiting...")
            return

        # Tilataan notifikaatiot ja odotetaan
        try:
            logging.info(f"Starting notifications until {max_sample_count} samples have been captured.")
            await client.start_notify(uuid, notification_handler)
            await stop_event.wait()
        finally:
            logging.info("Stopping notifications...")
            await client.stop_notify(uuid)
            logging.info("Writing samples to file...")
            process_captured_packets() # Tallentaa pakettien sisältämät samplet tiedostoon

try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.warning("Interrupted")
finally:
    logging.info("Exiting...")
