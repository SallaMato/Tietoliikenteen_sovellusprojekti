# Tietoliikenteen_sovellusprojekti

Projektin tavoitteena on suunnitella Thingylle client, joka mittaa anturidataa kiihtyvyysanturista (GY-61 (ADXL335) 3-akselinen kiihtyvyysanturi) ja välittää tietoa langattomasti IoT-reitittimelle (Raspberry Pi). Raspberry välittää dataa omalle MySQL palvelimelle. Tietokantaan tallentyvaan dataan on TCP-socket rajapinta ja yksinkertainen HTTP API. Kerättyä dataa haetaan HTTP-rajapinnasta omalle kannettavalle koodatulla ohjelmalla ja käsitellään koneoppimistarkoituksiin. Toteutuksessa käytetään nRF5340DK -kehitysalustaa.

Lisäominaisuutena toteutetaan laite kynän päähän kiinnitettävä laite, joka kerää dataa kynän liikkeestä koneoppimismallille joka tunnistaa kynällä piirretyt kuviot.

## Viikko 1

Projektin suunnittelu ja valmistelu sekä Projektin arkkitehtuuri (v0.1)

<img width="845" height="715" alt="image" src="https://github.com/user-attachments/assets/fe459390-b74b-458d-b7c3-0289d769b75c" />


## Viikko 2

Viikon 2 tavoitteena oli siirtää kiihtyvyysanturin data (x,y,z) Bluetooth Low Energy (BLE) - yhteyden yli puhelimeen tai tietokoneeseen. Osana viikon 2 toteutusta jokainen projektin tekijä suoritti Nordic Academyn - Bluetooth Fundamentals -verkkokurssin.

Lisäominaisuutta varten datan keräys suoritettiin harjoituskoodien jälkeen nRF Connect SDK Intermediate -verkkokurssin Lesson 6 (Analog-to-digital converter (ADC)) Exercise 3 (Interfacing with ADC using nrfx drivers and TIMER/PPI) koodipohjan päälle. Tämä mahdollisti nopeamman datan keräyksen kahden puskurin (ping-pong -keräys) ja Advanced moden avulla. Advanced mode yhdistää laitteistotason ajastimen, ADC:n ja EasyDMA:n. Ajastin laukaisee ADC:n automaattisesti taustalla ja ADC tallentaa tulokset suoraan RAM-muistiin puskuriin herättämättä prosessoria. Prosessori herää vasta sitten, kun koko puskuri on täynnä, jolloin prosessori voi lähettää sen kerralla Bluetoothilla. Puskurin kooksi valittiin 240 tavua, joka mahtuu BLE pakettirajaan. Tällä ratkaisulla onnistuimme keräämään 16 000 näytettä sekunnissa.

## Viikko 3

Viikolla 3 toteutimme MySQL tietokannan omalle Ubuntu Linux -palvelimelle. Teimme Python - ohjelman Raspberrylle, joka vastaanottaa dataa Bluetoothia käyttäen Nordicin alustalta ja lähettää sen MySQL - tietokantaan. 

Datan hakemiseksi tietokannasta toteutimme kahdella tavalla: Python - skripti, joka hakee datan suoraan tietokannasta MySQL-rajapinnan kautta, sekä TCP-asiakasohjelma Pythonilla, joka hakee, käsittelee ja tallentaa HTTP-siirron yli datan omalle kannettavalle CSV-tiedostoksi.

## Viikko 4

## Viikko 5

Kmeans luokittelija, CNN (Datan kerääminen ja valmistelu, Datasetin muodostus, CNN:n opetus, Mallin arviointi ja tallennus)

## Viikko 6

Kmeans luokittelija algoritmi, CNN:n toteutus NRF5340KD-mikrokontrollerissa

