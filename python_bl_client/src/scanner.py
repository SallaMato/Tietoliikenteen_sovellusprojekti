'''
Ohjelma skannaa BLE laitteita ja tulostaa niiden nimen ja osoitteen.

Alustus (tarvitsee tehdä vain kerran):
1: Kannattaa ensin tehdä python environment komennolla:
   python -m venv /path/to/new/virtual/environment   <-- muokkaa tiedostopolku osoittamaan "python_bl_client" -kansioon

2: Aiempi komento luo "Scripts" kansion. Aja komentokehotteella "Scripts" kansiossa "activate.bat" -komento.
   Tämä aktivoi python environmentin. Tiedät että olet environmentissa kun komentokehotteeseen tulee
   "(python_bl_client)" etuliite. Nyt kaikki moduuliasennukset (pip install <module>) asentuvat vain tälle
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
