# Tietoliikenteen sovellusprojekti

Langaton anturidatan keräys- ja tallennusjärjestelmä, joka hyödyntää Nordic nRF5340DK -alustaa, Bluetooth Low Energy (BLE) -tiedonsiirtoa, Raspberry Pi -yhdyskäytävää sekä MySQL-tietokantaa. Järjestelmän tavoitteena on kerätä kiihtyvyysanturidataa ja tarjota rajapinnat datan jatkokäsittelyyn sekä koneoppimissovelluksiin.

## Projektin tavoite

Projektin tavoitteena oli toteuttaa järjestelmä, joka:

- Mittaa kiihtyvyysdataa ADXL335 (GY-61) -anturilta
- Välittää datan Bluetooth Low Energyn avulla Raspberry Pi -reitittimelle
- Tallentaa vastaanotetun datan MySQL-tietokantaan
- Tarjoaa HTTP- ja TCP-pohjaiset rajapinnat datan hakemista varten
- Mahdollistaa datan keräämisen koneoppimismallien opettamiseen

Lisäominaisuutena toteutettiin kynään kiinnitettävä mittauslaite, jonka avulla voidaan kerätä liikedataa käsin piirrettyjen kuvioiden tunnistamista varten.

## Projektin suunnittelu ja valmistelu sekä Projektin arkkitehtuuri (v0.1)

<img width="845" height="715" alt="image" src="https://github.com/user-attachments/assets/fe459390-b74b-458d-b7c3-0289d769b75c" />

---

## Käytetyt teknologiat
| Komponentti           | Teknologia                    |
|-----------------------|-------------------------------|
| Sulautettu alusta     | Nordic nRF5340DK              |
| Kiihtyvyysanturi      | ADXL335 (GY-61)               |
| Langaton tiedonsiirto | Bluetooth Low Energy 5.0      |
| IoT-yhdyskäytävä      | Raspberry Pi                  |
| Tietokanta            | MySQL                         |
| Rajapinnat            | HTTP, TCP Socket              |
| Ohjelmointikielet     | Python, C                     |
| Ohjelmointikirjastot  | Bleak, mysql-connector-python |

## Analogisen datan keräys
Viikon 2 tavoitteena oli siirtää kiihtyvyysanturin data (x,y,z) Bluetooth Low Energy (BLE) - yhteyden yli puhelimeen tai tietokoneeseen. Osana viikon 2 toteutusta jokainen projektin tekijä suoritti Nordic Academyn - Bluetooth Fundamentals -verkkokurssin.

Lisäominaisuutta varten datan keräys suoritettiin harjoituskoodien jälkeen nRF Connect SDK Intermediate -verkkokurssin Lesson 6 (Analog-to-digital converter (ADC)) Exercise 3 (Interfacing with ADC using nrfx drivers and TIMER/PPI) koodipohjan päälle. Tämä mahdollisti nopeamman datan keräyksen kahden puskurin (ping-pong -keräys) ja Advanced moden avulla. Advanced mode yhdistää laitteistotason ajastimen, ADC:n ja EasyDMA:n. Ajastin laukaisee ADC:n automaattisesti taustalla ja ADC tallentaa tulokset suoraan RAM-muistiin puskuriin herättämättä prosessoria. Prosessori herää vasta sitten, kun koko puskuri on täynnä, jolloin prosessori voi lähettää sen kerralla Bluetoothilla. Puskurin kooksi valittiin 240 tavua, joka mahtuu BLE pakettirajaan. Tällä ratkaisulla onnistuimme keräämään 16 000 näytettä sekunnissa.

## BLE tiedonsiirto
Anturidata lähetetään BLE-notifikaatioina 241 tavun paketeissa.

### Paketin rakenne:
| Offset  | Arvo   | Datatyyppi | Koko (tavuina) | Kuvaus                     |
|---------|--------|------------|----------------|----------------------------|
| 0       | Suunta | uint8_t    | 1              | Käyttäjän valitsema suunta |
| 1-2     | X0     | uint16_t   | 2              | Kiihtyvyysanturin x-arvo   |
| 3-4     | Y0     | uint16_t   | 2              | Kiihtyvyysanturin y-arvo   |
| 5-6     | Z0     | uint16_t   | 2              | Kiihtyvyysanturin z-arvo   |
| ...     | ...    | ...        | ...            | ...                        |
| 235-236 | X39    | uint16_t   | 2              | Kiihtyvyysanturin x-arvo   |
| 237-238 | Y39    | uint16_t   | 2              | Kiihtyvyysanturin y-arvo   |
| 239-240 | Z39    | uint16_t   | 2              | Kiihtyvyysanturin z-arvo   |

Jotta BLE stack kykeni lähettämään suuria paketteja tarpeeksi nopeasti, tuli oletusasetuksia
muuttaa. Tämä onnistui connection parametrien avulla. Apuna käytetiin BLE Fundamentals kurssin
Lesson 3 Exercise 4 tehtävää. Tärkeimmät asetukset olivat:
| Parametri           | Arvo   |
|---------------------|--------|
| Connection Interval | 7.5 ms |
| Data Length         | 251 B  |
| ATT MTU             | 247 B  |
| PHY Mode            | 2M     |

Huomioitavaa on, että asetukset eivät ole pelkästään nrf5340 alustan
päätettävissä, vaan ne täytyy neuvotella "central" -laitteen kanssa, eli laitteen
joka ottaa datan vastaan.

## Python ohjelmat ja rajapinnat
### python_ble_csv_client
Viikolla 2 toteutetut python koodit. Tässä kansiossa on kolme eri
python scriptiä, jotka hyödyntävät Bleak kirjastoa: scanner.py,
timer_client.py ja ble_csv_client.py. 

#### scanner.py
Skannaa bluetooth laitteita ja tulostaa niiden nimet ja osoitteet
terminaaliin.

#### timer_client.py
Nappaa nrf5340 laitteen lähettämiä BLE paketteja ja tallentaa näytteet
.csv tiedostoon. Käyttää ajastinta joka lopettaa pakettien nappaamisen
kun annettu aika on kulunut. Tätä ohjelmaa ei kuitenkaan lopulta
käytetty mihinkään, sillä ajastimeen perustuvalla ohjelmalla ei voinut
luotettavasti saada napattua juuri oikeaa määrää näytteitä.

Ohjelman toimintaa voi säätää .env tiedoston avulla muuttujilla:

DEVICE_ADDR=""
- BLE laitteen (nrf5340) bluetooth osoite.
  
CHARACTERISTIC_UUID=""
- Kiihtyvyysdatan characteristic uuid koodi.
  
PACKET_DATA_LEN_BYTES=""
- BLE paketin koko tavuina.
  
TIMER_SECONDS=""
- Kuinka kauan ohjelma nappaa paketteja.

#### ble_csv_client.py
Nappaa nrf5340 laitteen lähettämiä BLE paketteja ja tallentaa näytteet
.csv tiedostoon. Käyttäjä voi itse määritellä kuinka monta yksittäistä
näytettä (x,y,z kolmiarvoa) haluaa napata. Näytteet tallennetaan .csv
tiedostoon.

Ohjelman toimintaa voi säätää .env tiedoston avulla muuttujilla:

DEVICE_ADDR=""
- BLE laitteen (nrf5340) bluetooth osoite.
  
CHARACTERISTIC_UUID=""
- Kiihtyvyysdatan characteristic uuid koodi.
  
PACKET_DATA_LEN_BYTES=""
- BLE paketin koko tavuina.

MAX_SAMPLE_COUNT=""
- Kuinka monta yksittäistä (x,y,z) näytettä halutaan napata.

### python_ble_sql_client
Viikolla 3 toteutettu ohjelma. Vastaanottaa Nordic alustan (nRF5340dk)
lähettämää BLE dataa, ja tallentaa sen MySQL tietokantaan. Ohjelmassa
pyrittiin erottelemaan BLE pakettien vastaanottaminen ja tietokantaan
tallentaminen omille säikeille, niin että ne eivät hidastaisi
toisiaan. Tämä onnistui Bleak kirjaston ja asyncio kirjaston avulla.
Apuna käytettiin myös myql-connector python kirjastoa.

Ohjelman toimintaa voi säätää .env tiedoston avulla muuttujilla:

DEVICE_ADDR=""
- BLE laitteen (nrf5340) bluetooth osoite.
  
CHARACTERISTIC_UUID=""
- Kiihtyvyysdatan characteristic uuid koodi.

PACKET_DATA_LEN_BYTES=""
- BLE paketin koko tavuina.  

MAX_SAMPLE_COUNT=""
- Kuinka monta yksittäistä (x,y,z) näytettä halutaan napata.

MYSQL_ADDR=""
- MySQL tietokannan IP osoite.

MYSQL_PORT=""
- MySQL tietokannan portti.

MYSQL_USER=""
- MySQL tietokannan käyttäjänimi.

MYSQL_PASS=""
- MySQL tietokannan käyttäjän salasana.

MYSQL_DB_NAME=""
- MySQL tietokannan nimi.

### python_sql_client
Viikolla 3 toteutettu python ohjelma, joka hakee dataa suoraan
MySQL tietokannasta (10 riviä) ja tulostaa ne terminaaliin.

Ohjelman toimintaa voi säätää .env tiedoston avulla muuttujilla:

MYSQL_ADDR=""
- MySQL tietokannan IP osoite.

MYSQL_PORT=""
- MySQL tietokannan portti.

MYSQL_USER=""
- MySQL tietokannan käyttäjänimi.

MYSQL_PASS=""
- MySQL tietokannan käyttäjän salasana.

MYSQL_DB_NAME=""
- MySQL tietokannan nimi.

### python_tcp_client
Viikolla 3 toteutettu TCP-asiakasohjelma, joka hakee
HTTP protokollaa käyttäen dataa omalta serveriltä.
Serverillä oleva php script antaa anturimittausdataa, jonka
sitten asiakasohjelma tallentaa .csv tiedostoon.

### python_tcp_socket_client
Viikolla 4 toteutettu TCP socket ohjelma, joka
yhdistää palvelimen tcp porttiin 20000, ja lähettää sinne
oman id numeron. Palvelimella pyörivä ohjelma lähettää id:tä
vastaavaa dataa takaisin. Tämä data tallennetaan tekstitiedostoon.

### python_ble_binary_client
Viikolla 5 toteutettu ohjelma, joka on muuten samankaltainen kuin
viikolla 2 toteutettu python_ble_csv_client, mutta tallentaa datan
binäärimuodossa (.npy) tiedostoon. Optimoitu niin että bluetooth
pakettien nappaaminen on mahdollisimman tehokasta, jotta pysytään
suuren näytteenottotaajuuden mukana. Ohjelmaa käytettiin datan
keräämiseen koneoppimismallia varten.

Ohjelman toimintaa voi säätää .env tiedoston avulla muuttujilla:

DEVICE_ADDR=""
- BLE laitteen (nrf5340) bluetooth osoite.
  
CHARACTERISTIC_UUID=""
- Kiihtyvyysdatan characteristic uuid koodi.
  
PACKET_DATA_LEN_BYTES=""
- BLE paketin koko tavuina.

MAX_SAMPLE_COUNT=""
- Kuinka monta yksittäistä (x,y,z) näytettä halutaan napata.

LABEL=""
- Minkä nimiseen alikansioon data halutaan tallentaa.

## Palvelimet, tietokannat ja raspberry PI reititin
Projektissa oli käytössä kaksi virtuaalista Ubuntu palvelinta.
Toinen oli tarkoitettu testikäyttöön ja toinen tuotantoon. Palvelimille
asennettiin MySQL tietokannat.

Raspberry PI toimi palvelimien ja nrf5340 laitteen välissä. Sen
tehtävänä oli vastaanottaa BLE dataa, välittää anturidata
palvelimille, jotka sitten tallensivat sen tietokantaan.

## Koneoppimissovellus
<Tähän voisi kirjoittaa koneoppimismallista jotain>
