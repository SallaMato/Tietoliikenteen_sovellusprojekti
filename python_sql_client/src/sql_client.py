'''
Hakee tietokannasta 10 ensimmäistä riviä
'''

import os
from dotenv import load_dotenv
import mysql.connector

# Ladataan ympäristömuuttujat .env tiedostosta.
load_dotenv()

# Haetaan .env tiedostosta muuttujat.
device_addr = os.getenv("DEVICE_ADDR")
uuid = os.getenv("CHARACTERISTIC_UUID")
packet_data_len_bytes = int(os.getenv("PACKET_DATA_LEN_BYTES"))
max_sample_count = int(os.getenv("MAX_SAMPLE_COUNT"))

mysql_addr= os.getenv("MYSQL_ADDR")
mysql_port= int(os.getenv("MYSQL_PORT"))
mysql_user= os.getenv("MYSQL_USER")
mysql_pass= os.getenv("MYSQL_PASS")
mysql_db_name = os.getenv("MYSQL_DB_NAME")

# MySQL yhteyden asetukset
config = {
    "host": mysql_addr,
    "port": mysql_port,
    "user": mysql_user,
    "password": mysql_pass,
    "database": mysql_db_name,
    "use_pure": True,
    "autocommit": False
}

cnx = mysql.connector.connect(**config)
cursor = cnx.cursor()

stmt = """
SELECT *
FROM rawdata
LIMIT 10;
"""

cursor.execute(stmt)
    
for (id, timestamp, groupid, from_mac, to_mac, sensorvalue_a, sensorvalue_b, sensorvalue_c, sensorvalue_d, sensorvalue_e, sensorvalue_f) in cursor:
    print('{:5} {:10} {:2} {:20} {:20} {:5} {:5} {:5} {:5} {:5} {:20}'.format(
    id, timestamp, groupid, from_mac, to_mac,
    sensorvalue_a, sensorvalue_b,
    sensorvalue_c, sensorvalue_d,
    sensorvalue_e, sensorvalue_f))

cursor.close()
cnx.close()
