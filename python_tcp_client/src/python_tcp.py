import requests

#URL 

url = f"http://172.20.241.107/hae_data_tcp.php"

try:
    #HTTP GET -pyyntö palvelimelle
    vastaus = requests.get(url)

    #Tarkistetaan, että pyyntö onnistui (HTTP 200 OK)
    #Jos tulee virhe (404) tulee error
    vastaus.raise_for_status()

    #Määritetään paikallisen tiedoston nimi
    tiedostonimi = f"mittausdata_tcp.csv"

    #Avataan tiedosto kirjoitustilassa ("w") ja tallennetaan data
    with open(tiedostonimi, "w", encoding="utf-8") as tiedosto:
        tiedosto.write(vastaus.text)

except requests.exceptions.RequestException as e:
    print(f"Virhe yhteydnotossa palvelimeen: {e}")