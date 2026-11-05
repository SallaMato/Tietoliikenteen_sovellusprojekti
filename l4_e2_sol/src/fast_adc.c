/* Alkuperäinen adc koodissa main.c pyysi arvon ADC:ltä. ADC luki arvon ja antoi sen takaisin. Tämä tapa on helppo, mutta hidas.
Uudella menetelmällä laitteisto kerää dataa taustalla satoja kertoja sekunnissa. Kun 300 arvon puskuri on täynnä, tapahtuu keskeytys (interrupt).
Keskeytys pysäyttää prosessorin nanosekunneissa ja pakottaa sen suorittamaan saadc_event_handler funktion.
Keskeytyksen aikana ei saa lähettää BLE yli tai tulostaa sarjaporttiin, koska muuten laite jumiutuu.

Ratkaisuna käytetään viestijonoa (Message Queue). Zephyr käyttöjärjestelmässä on tätä varten työkalu k_msgq.*/


#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <nrfx_saadc.h>
#include <nrfx_timer.h>
#include <helpers/nrfx_gppi.h>

#include "fast_adc.h"

LOG_MODULE_REGISTER(FastADC, LOG_LEVEL_INF);

/* STEP 3.1 - Define the SAADC sample interval in microseconds */
// 16 000 näytettä varten kahden jakson välinen aika olisi 62,5us. Tässä voi käyttää vain kokonaislukuja, joten pyöristetään.
//Voi myös kokeilla muuttaa ajastimen käyttämään suoraan ajastimen kelloa.
#define SAADC_SAMPLE_INTERVAL_US 62

/* STEP 4.1 - Define the buffer size for the SAADC */
// SAADC tallentaa dataa puskuriin saadc_sample_buffer. Kun mitataan kolmea kanavaa, joka kerta kun ajastin laukaisee
// SAADC ottaa kolme näytettä (x, y, z) ja laittaa ne puskuriin peräkkäin ([X1, Y1, Z1, X2, Y2, Z2,..]).
//Jos halutaan kerätä 16 000 näytettä kolmelta kanavalta, tarvitaan 16 000 * 3 = 48 000 arvoa sekunnissa. Laitteen muisti todennäköisesti loppuisi
//joten käytetään mallipohjan pingpong-puskuria.
// --> laitteisto täyttää puskuria 0, ja kun se on täynnä, tapahtuu NRFX_SAADC_EVT_DONE - keskeytys, ja laitteisto alkaa automaattisesti
//täyttämään puskuria 1. Keskeytyksen aikana voidaan lähettää puskurin 0 data eteenpäin.
// Asetetaan puskurin kooksi 300 (100 näytettä * 3)
// 5.11 muutettu paketin kooksi 120 (40 näytettä * 3) koska 120 arvoa * 2 (uint16) = 240 tavua -> tämä mahtuu BLE paketti rajaan
#define SAADC_BUFFER_SIZE   120

// Luodaan Message Queue.
// Määritellään jono 'fast_adc_msgq' joka ottaa vastan 'struct fast_adc_msg' tyyppisiä viestejä.
// Jonoon mahtuu kerrallaan 4 viestiä.
K_MSGQ_DEFINE(fast_adc_msgq, sizeof(struct fast_adc_msg), 4, 4);

static nrfx_timer_t timer_instance = NRFX_TIMER_INSTANCE(NRF_TIMER2);
static int16_t saadc_sample_buffer[2][SAADC_BUFFER_SIZE];
static uint32_t saadc_current_buffer = 0;

//Määritellään kolme kanavaa, joista luetaan x, y ja z akselin arvoja
static nrfx_saadc_channel_t channels[3] = {
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRFX_ANALOG_EXTERNAL_AIN0, 0),
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRFX_ANALOG_EXTERNAL_AIN1, 1),
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRFX_ANALOG_EXTERNAL_AIN2, 2)
};


static void configure_timer(void)
{
    int err;
    nrfx_timer_config_t timer_config = NRFX_TIMER_DEFAULT_CONFIG(1000000);
    err = nrfx_timer_init(&timer_instance, &timer_config, NULL);

    uint32_t timer_ticks = nrfx_timer_us_to_ticks(&timer_instance, SAADC_SAMPLE_INTERVAL_US);
    nrfx_timer_extended_compare(&timer_instance, NRF_TIMER_CC_CHANNEL0, timer_ticks, NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, false);
}

static void saadc_event_handler(nrfx_saadc_evt_t const * p_event)
{
    switch (p_event->type)
    {
        case NRFX_SAADC_EVT_READY:
            nrfx_timer_enable(&timer_instance);
            break;                        
            
        case NRFX_SAADC_EVT_BUF_REQ:
            nrfx_saadc_buffer_set(saadc_sample_buffer[(saadc_current_buffer++)%2], SAADC_BUFFER_SIZE);
            break;

        case NRFX_SAADC_EVT_DONE:
        {
            // Kun puskuri on täynnä, luodaan viesti (struct fast_adc_msg) ja laitetaan se viestijonoon (k_msgq_put).
            struct fast_adc_msg msg;
            msg.buffer = (int16_t *)p_event->data.done.p_buffer;
            msg.size = p_event->data.done.size;

            // k_msgq_put laittaa viestin jonoon. K_NO_WAIT tarkoittaa, että jos jono on aivan täynnä, keskeytys ei jää odottamaan, vaan jatkaa matkaa.
            k_msgq_put(&fast_adc_msgq, &msg, K_NO_WAIT);
        }
        break;
        
        default:
            break;
    }
}

static void configure_saadc(void)
{
    int err;

    /*  Yhdistetään ADC:n keskeytys Zephyrin järjestelmään */
    IRQ_CONNECT(DT_IRQN(DT_NODELABEL(adc)),
                DT_IRQ(DT_NODELABEL(adc), priority),
                nrfx_isr, nrfx_saadc_irq_handler, 0);

    /*  Alustetaan ADC-ajuri */
    err = nrfx_saadc_init(DT_IRQ(DT_NODELABEL(adc), priority));
    if (err != 0) {
        LOG_ERR("nrfx_saadc_init error: %08x", err);
        return;
    }

    channels[0].channel_config.gain = NRF_SAADC_GAIN1_6;
    channels[1].channel_config.gain = NRF_SAADC_GAIN1_6;
    channels[2].channel_config.gain = NRF_SAADC_GAIN1_6;
    
    /* Ladataan kanavien X, Y ja Z asetukset ADC:lle */
    err = nrfx_saadc_channels_config(channels, 3);
    if (err != 0) {
        LOG_ERR("nrfx_saadc_channels_config error: %08x", err);
        return;
    }

    /*  Määritetään Advanced mode ja aktivoidaan kanavat 0, 1 ja 2.
    BIT(0) on X, BIT(1) on Y, BIT(2) on Z. 
    Advanced mode: Yhdistää laitteistotason ajastimen, ADC:n ja EasyDMA:n (suora muistiosoitus). 
    Ajastin laukaisee ADC:n automaattisesti taustalla, ja ADC tallentaa tulokset suoraan RAM-muistiin puskuriin herättämättä prosessoria. 
    Prosessori herää vasta sitten, kun koko puskuri (esim. 300 arvoa) on täynnä, jolloin prosessori voi lähettää sen kerralla Bluetoothilla.*/
    nrfx_saadc_adv_config_t saadc_adv_config = NRFX_SAADC_DEFAULT_ADV_CONFIG;
    err = nrfx_saadc_advanced_mode_set(BIT(0) | BIT(1) | BIT(2),
                                       NRF_SAADC_RESOLUTION_12BIT,
                                       &saadc_adv_config,
                                       saadc_event_handler);
    if (err != 0) {
        LOG_ERR("nrfx_saadc_advanced_mode_set error: %08x", err);
        return;
    }
                                            
    /* Asetetaan kaksi puskuria ping-pong -keräystä varten */
    err = nrfx_saadc_buffer_set(saadc_sample_buffer[0], SAADC_BUFFER_SIZE);
    if (err != 0) {
        LOG_ERR("nrfx_saadc_buffer_set 0 error: %08x", err);
        return;
    }
    err = nrfx_saadc_buffer_set(saadc_sample_buffer[1], SAADC_BUFFER_SIZE);
    if (err != 0) {
        LOG_ERR("nrfx_saadc_buffer_set 1 error: %08x", err);
        return;
    }

    /*Asetetaan ADC valmiustilaan odottamaan ajastimen liipaisua */
    err = nrfx_saadc_mode_trigger();
    if (err != 0) {
        LOG_ERR("nrfx_saadc_mode_trigger error: %08x", err);
        return;
    }
}

static void configure_ppi(void)
{
    int err;
    /* STEP 6.1 - Declare variables used to hold the (D)PPI channel number */
    nrfx_gppi_handle_t gppi_handle_sample;
    nrfx_gppi_handle_t gppi_handle_start;

    /* STEP 6.2 - Trigger task sample from timer */
    err = nrfx_gppi_conn_alloc( nrfx_timer_compare_event_address_get(&timer_instance, NRF_TIMER_CC_CHANNEL0),nrf_saadc_task_address_get(NRF_SAADC, NRF_SAADC_TASK_SAMPLE), &gppi_handle_sample);
    if (err != 0) {
        LOG_ERR("nrfx_gppi_conn_alloc error: %08x", err);
        return;
    }

    /* STEP 6.3 - Trigger task start from end event */
    err = nrfx_gppi_conn_alloc(nrf_saadc_event_address_get(NRF_SAADC, NRF_SAADC_EVENT_END),nrf_saadc_task_address_get(NRF_SAADC, NRF_SAADC_TASK_START), &gppi_handle_start);
    if (err != 0) {
        LOG_ERR("nrfx_gppi_conn_alloc error: %08x", err);
        return;
    }

    /* STEP 6.4 - Enable both (D)PPI channels */ 
    nrfx_gppi_conn_enable(gppi_handle_sample);
    nrfx_gppi_conn_enable(gppi_handle_start);
}


// Funktio, jota main.c kutsuu. Käynnistää ajastimen ja ADC:n
void fast_adc_init_and_start(void)
{
    configure_timer();
    configure_saadc();  
    configure_ppi();
}