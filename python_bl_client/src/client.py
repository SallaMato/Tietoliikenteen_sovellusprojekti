import sys
import asyncio
from bleak import BleakClient

addr = "DE:8D:ED:BD:1A:D0"
char_uuid = "00001526-1212-efde-1523-785feabcd123"

def notification_handler(sender, data):
    print(f"Notification from {sender}: {data.hex()}")

async def main():
    async with BleakClient(addr) as client:

        # Discover services and characteristics
        for service in client.services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(
                    f"  Characteristic: {char.uuid} "
                    f"properties={char.properties}"
                )
        
        # Subscribe using UUID
        await client.start_notify(
            char_uuid,
            notification_handler
        )

        print("Subscribed. Waiting for notifications...")
        # Jos halutaan pysayttaa:
        '''
        await asyncio.sleep(60000)

        await client.stop_notify(
            "00001526-1212-efde-1523-785feabcd123"
        )
        '''

asyncio.run(main())
