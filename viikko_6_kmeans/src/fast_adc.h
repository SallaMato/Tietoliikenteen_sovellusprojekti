/* Alkuperäinen adc koodissa main.c pyysi arvon ADC:ltä. ADC luki arvon ja antoi sen takaisin. Tämä tapa on helppo, mutta hidas.
Uudella menetelmällä laitteisto kerää dataa taustalla satoja kertoja sekunnissa. Kun 300 arvon puskuri on täynnä, tapahtuu keskeytys (interrupt).
Keskeytys pysäyttää prosessorin nanosekunneissa ja pakottaa sen suorittamaan saadc_event_handler funktion.
Keskeytyksen aikana ei saa lähettää BLE yli tai tulostaa sarjaporttiin, koska muuten laite jumiutuu.

Ratkaisuna käytetään viestijonoa (Message Queue). Zephyr käyttöjärjestelmässä on tätä varten työkalu k_msgq.*/

#ifndef FAST_ADC_H_
#define FAST_ADC_H_

#include <zephyr/kernel.h>

// Paketti, joka lähetetään keskeytyksestä main.c:lle.
// Paketti ei sisällä dataa, koska se olisi liian hidasta kopioida.
// --> Paketti sisältää vain osoittimen (pointer) siihen RAM-muistin kohtaan, jossa data on
struct fast_adc_msg {
    int16_t *buffer; // Osoite RAM-muistiin, jossa 300 arvoa ovat
    uint16_t size;   // Arvojen määrä (esim. 300)
};


// Funktio, jota main.c kutsuu käynnistääkseen keräyksen.
void fast_adc_init_and_start(void); 

#endif