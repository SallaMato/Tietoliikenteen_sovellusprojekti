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
logging.basicConfig(level=logging.INFO)

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
    os.makedirs(f"../data/{label}", exist_ok=True)
    filename = f"../data/{label}/data_{label}_S{max_sample_count}_{int(time.time())}.npy"

    # Kerätään kaikki näytteet ensin yhteen (16000, 3) taulukkoon
    all_samples = np.zeros((max_sample_count, 3), dtype=np.uint16)
    sample_count = 0

    for packet in packets:
        for i in range(samples_per_packet):
            if sample_count >= max_sample_count:
                break
            all_samples[sample_count] = struct.unpack_from('HHH', packet, 1 + i * 6)
            sample_count += 1
        if sample_count >= max_sample_count:
            break

    # Tallennetaan koko taulukko yhdellä kertaa oikeassa (16000, 3) muodossa
    np.save(filename, all_samples)
    logging.info(f"Tallennettu {sample_count} näytettä -> {filename} (muoto: {all_samples.shape})")


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

    if packet_count >= num_packets_to_capture:
        if shutdown_requested == False:
            request_shutdown()

async def main():

    global packet_count, shutdown_requested, last_time
    saved_files = 0

    async with BleakClient(addr) as client:
        if not uuid:
            logging.error("uuid not given, exiting...")
            return

# Tilataan notifikaatiot vain kerran alussa
        await client.start_notify(uuid, notification_handler)
        try:
            while True:
                # Nollataan laskurit uutta näytettä varten
                packet_count = 0
                shutdown_requested = False
                last_time = None
                stop_event.clear()

                logging.info(f"\n>>> Valmiina näytteeseen #{saved_files + 1} (kirjain {label}). <<<")
                await stop_event.wait()

                logging.info("Kirjoitetaan näyte tiedostoon...")
                process_captured_packets()
                saved_files += 1

                # Pieni tauko, jotta mahdolliset ylijäämäpaketit eivät mene seuraavaan näytteeseen
                await asyncio.sleep(1.0)
        finally:
            logging.info("Stopping notifications...")
            await client.stop_notify(uuid)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.warning("Lopetettu käyttäjän toimesta (Ctrl+C)")
finally:
    logging.info("Exiting...")
