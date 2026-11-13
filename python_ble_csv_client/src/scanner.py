'''
Ohjelma skannaa BLE laitteita ja tulostaa niiden nimen ja osoitteen.

Alustus (tarvitsee tehdä vain kerran):
1: Kannattaa ensin tehdä "python_bl_client" kansiossa python environment komennolla:
   python -m venv .venv

2: Aiempi komento luo ".venv/Scripts" kansion. Aja sieltä "activate.bat" -komento.
   Tämä aktivoi python environmentin. Tiedät että olet environmentissa kun komentokehotteeseen tulee
   "(.venv)" etuliite. Nyt kaikki moduuliasennukset (pip install <module>) asentuvat vain tälle
   environmentille paikallisesti.
  
3: Kokeile ajaa "scanner.py". Todennäköisesti saat virheen "ModuleNotFoundError: No module named 'bleak'".
   Voit asentaa sen "pip install bleak" -komennolla. Toista sama mahdollisten muiden puuttuvien moduuleiden
   kohdalla.

Esimerkki ohjelman ajamisesta:
1: Varmista että olet aktivoinut environmentin, eli aja komento "Scripts/activate.bat".

2: Aja komento "python scanner.py"
'''

import asyncio
from bleak import BleakScanner

async def main():
  devices = await BleakScanner.discover(timeout=5.0)
  print(f'{"DEVICE":30}  ADDRESS')
  for device in devices:
    print(f'{(device.name or "Unknown"):30}  {device.address}')

asyncio.run(main())
