#include <zephyr/kernel.h>
#include <math.h>
#include "confusion.h"
#include "keskipisteet.h"

int CM[6][6]= {0};

void printConfusionMatrix(void)
{
	printk("Confusion matrix = \n");
	printk("   cp1 cp2 cp3 cp4 cp5 cp6\n");
	for(int i = 0;i<6;i++)
	{
		printk("cp%d %d   %d   %d   %d   %d   %d\n",i+1,CM[i][0],CM[i][1],CM[i][2],CM[i][3],CM[i][4],CM[i][5]);
	}
}

void makeHundredFakeClassifications(void)
{
   /*******************************************
   Jos ja toivottavasti kun teet toteutuksen paloissa eli varmistat ensin,
   että etäisyyden laskenta 6 keskipisteeseen toimii ja osaat valita 6 etäisyydestä
   voittajaksi sen lyhyimmän etäisyyden, niin silloin voit käyttää tätä aliohjelmaa
   varmistaaksesi, että etäisuuden laskenta ja luokittelu toimii varmasti tunnetulla
   itse keksimälläsi sensoridatalla ja itse keksimilläsi keskipisteillä.
   *******************************************/
   printk("Make your own implementation for this function if you need this\n");
}

void makeOneClassificationAndUpdateConfusionMatrix(int direction)
{
   /**************************************
   Tee toteutus tälle ja voit tietysti muuttaa tämän aliohjelman sellaiseksi,
   että se tekee esim 100 kpl mittauksia tai sitten niin, että tätä funktiota
   kutsutaan 100 kertaa yhden mittauksen ja sen luokittelun tekemiseksi.
   **************************************/
   printk("Make your own implementation for this function if you need this\n");
}

void classifyAndUpdateConfusionMatrix(uint8_t* payload, int payload_len)
{
   /**************************************
   Luokittelee annetun payloadin sisältämän kiihtyvyysanturi datan
   suunnan.
   **************************************/
   if(!payload)
      return;

   // Payloadin ensimmäinen tavu sisältää suunnan
   uint8_t actual_direction = payload[0];

   uint16_t* data_ptr = (uint16_t*)(payload + 1);
   int num_measurements = (payload_len - 1) / 6;
   for(unsigned int i = 0; i < num_measurements; ++i)
   {
      uint16_t* x = data_ptr;
      uint16_t* y = x + 1;
      uint16_t* z = y + 1;

      printk("x: %d, y: %d, z: %d\n", *x, *y, *z);
      int predicted_direction = 
         calculateDistanceToAllCentrePointsAndSelectWinner(*x, *y, *z);

      CM[actual_direction][predicted_direction] += 1;
      data_ptr += 3;
   }

   printk("Classified %d measurements. Press Button 4 to sent via serial.", 
      num_measurements);
}

int calculateDistanceToAllCentrePointsAndSelectWinner(int x,int y,int z)
{
   /***************************************
   Tämän aliohjelma ottaa yhden kiihtyvyysanturin mittauksen x,y,z,
   laskee etäisyyden kaikkiin 6 K-means keskipisteisiin ja valitsee
   sen keskipisteen, jonka etäisyys mittaustulokseen on lyhyin.
   ***************************************/

   // Oletaan aluksi että etäisyys ensimmäiseen keskipisteeseen on lyhin
   int winner_cp_index = 0;
   int min_distance = euclidean_distance(x, y, z, CP[0][0], CP[0][1], CP[0][2]);

   // Loopataan loput keskipisteet ja tarkistetaan löytyykö lyhyempi etäisyys
   for(unsigned int i = 1; i < 6; ++i)
   {
      // Lasketaan etäisyys keskipisteeseen
      int distance = euclidean_distance(x, y, z, CP[i][0], CP[i][1], CP[i][2]);
      if(distance < min_distance)
      {
         winner_cp_index = i;
         min_distance = distance;
      }
   }

   // Palautetaan voittavan keskipisteen indeksi
   // Tämä on siis indeksi keskipisteet.h tiedoston array muuttujaan.
   return winner_cp_index;
}

void resetConfusionMatrix(void)
{
	for(int i=0;i<6;i++)
	{ 
		for(int j = 0;j<6;j++)
		{
			CM[i][j]=0;
		}
	}
}

int euclidean_distance(int x1, int y1, int z1, int x2, int y2, int z2)
{
   int delta_x = x2 - x1;
   int delta_y = y2 - y1;
   int delta_z = z2 - z1;

   int distance = sqrt(pow(delta_x, 2) + pow(delta_y, 2) + pow(delta_z, 2));
   return distance;
}