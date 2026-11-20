/*
 * Copyright (c) 2023 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gap.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/conn.h>
#include <dk_buttons_and_leds.h>
#include "my_lbs.h"
#include "fast_adc.h"
//muistikopiointia varten (memcpy)
#include <string.h>

extern struct k_msgq fast_adc_msgq;

static const struct bt_le_adv_param *adv_param = BT_LE_ADV_PARAM(
	(BT_LE_ADV_OPT_CONN |
	 BT_LE_ADV_OPT_USE_IDENTITY), /* Connectable advertising and use identity address */
	800, /* Min Advertising Interval 500ms (800*0.625ms) */
	801, /* Max Advertising Interval 500.625ms (801*0.625ms) */
	NULL); /* Set to NULL for undirected advertising */

LOG_MODULE_REGISTER(Lesson4_Exercise2, LOG_LEVEL_INF);

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

#define RUN_STATUS_LED DK_LED1
#define CON_STATUS_LED DK_LED2
#define USER_LED DK_LED3
#define USER_BUTTON DK_BTN1_MSK
#define USER_BUTTON2 DK_BTN2_MSK


#define STACKSIZE 1024
#define PRIORITY 7

#define RUN_LED_BLINK_INTERVAL 1000
/* STEP 17 - Define the interval at which you want to send data at */
#define NOTIFY_INTERVAL 500
static bool app_button_state;
static struct k_work adv_work;
static bool should_collect_data = false;

//(0 = X alas, 1 = X ylos, 2 = Y alas, 3 = Y ylös, 4 = Z alas, 5 = Z ylös)
volatile int suunta = 0;

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
	BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),

};

static const struct bt_data sd[] = {
	BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_LBS_VAL),
};

static void adv_work_handler(struct k_work *work)
{
	int err = bt_le_adv_start(adv_param, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));

	if (err) {
		printk("Advertising failed to start (err %d)\n", err);
		return;
	}

	printk("Advertising successfully started\n");
}
static void advertising_start(void)
{
	k_work_submit(&adv_work);
}
static void recycled_cb(void)
{
	printk("Connection object available from previous conn. Disconnect is complete!\n");
	advertising_start();
}

static void app_led_cb(bool led_state)
{
	dk_set_led(USER_LED, led_state);
}

static bool app_button_cb(void)
{
	return app_button_state;
}

/* STEP 18.1 - Define the thread function  */
void send_data_thread(void)
{
	struct fast_adc_msg msg; //Muuttuja, johon tallennetaan viestijonosta luettu viesti (struct fast_adc_msg)

	//Luodaan BLE-paketti (1 tavu suunta + 240 tavua dataa = 241 tavua)

    uint8_t ble_payload[241];
	
	while (1) {

		// k_msgq_get pysäyttää tämän säikeen (se menee nukkumaan) K_FOREVER-ajaksi,
		// kunnes viestijonossa on viesti fast_adc.c:stä.
		// Kun viesti tulee, se tallentuu 'msg' muuttujaan.
		if (k_msgq_get(&fast_adc_msgq, &msg, K_FOREVER) == 0) {

			//Nyt data on kerätty. msg.buffer on taulukko (X, Y,Z, X, Y,Z..) ja msg.size on 300.

			if (should_collect_data) {

				printk("Paketti saatu. Suunta: %d,Ensimmäinen näyte: X:%d Y:%d Z:%d\n", 
                     suunta, msg.buffer[0], msg.buffer[1], msg.buffer[2]);
				
				//Laitetaan suunta paketin ensimmäiseksi tavuksi
                ble_payload[0] = suunta;
				
				// Kopioidaan ADC-data (120 int16_t arvoa = 240 tavua) suunnan perään.
                // msg.buffer sisältää datan.
                memcpy(&ble_payload[1], msg.buffer, 240);

				//Lähetetään 241 tavun paketti BLE yli
				int err = my_lbs_send_payload(ble_payload, sizeof(ble_payload));
				if (err) {
    				printk("notify err: %d\n", err);
				}
			}
		}
	}
}

static struct my_lbs_cb app_callbacks = {
	.led_cb = app_led_cb,
	.button_cb = app_button_cb,
};

static void button_changed(uint32_t button_state, uint32_t has_changed)
{
	if (has_changed & USER_BUTTON) {
		uint32_t user_button_state = button_state & USER_BUTTON;
		/* STEP 6 - Send indication on a button press */
		my_lbs_send_button_state_indicate(user_button_state);
		app_button_state = user_button_state ? true : false;
		if (user_button_state) {
			suunta = (suunta + 1) % 6;
			
		} 
		
	}
	if (has_changed & USER_BUTTON2) {
		uint32_t user_button_state = button_state & USER_BUTTON2;
		/* STEP 6 - Send indication on a button press */
		//my_lbs_send_button_state_indicate(user_button_state);
		app_button_state = user_button_state ? true : false;
		should_collect_data = true;
		printk("Nappia 2 painettu");
	}
}

static void update_data_length(struct bt_conn *conn)
{
    int err;
    struct bt_conn_le_data_len_param data_len = {
        .tx_max_len = BT_GAP_DATA_LEN_MAX,
        .tx_max_time = BT_GAP_DATA_TIME_MAX,
    };
    err = bt_conn_le_data_len_update(conn, &data_len);
    if (err) {
        LOG_ERR("data_len_update failed (err %d)", err);
    }
}

static void on_connected(struct bt_conn *conn, uint8_t err)
{
	if (err) {
		printk("Connection failed (err %u)\n", err);
		return;
	}

	// Tällä ei ollut vaikutusta nopeuteen
	/*
    const struct bt_conn_le_phy_param preferred_phy = {
        .options = BT_CONN_LE_PHY_OPT_NONE,
        .pref_rx_phy = BT_GAP_LE_PHY_2M,
        .pref_tx_phy = BT_GAP_LE_PHY_2M,
    };

    int result = bt_conn_le_phy_update(conn, &preferred_phy);
    if (result) {
        LOG_ERR("bt_conn_le_phy_update() returned %d", err);
    }
	*/

	printk("Connected\n");
	dk_set_led_on(CON_STATUS_LED);
}

static void on_disconnected(struct bt_conn *conn, uint8_t reason)
{
	printk("Disconnected (reason %u)\n", reason);

	dk_set_led_off(CON_STATUS_LED);
}

static void on_param_updated(struct bt_conn *conn, uint16_t interval, 
	uint16_t latency, uint16_t timeout)
{
	struct bt_conn_info info;
    if (!bt_conn_get_info(conn, &info)) {
        printk("interval=%u\n",
               info.le.interval);
    }
}

void on_le_phy_updated(struct bt_conn *conn, struct bt_conn_le_phy_info *param)
{
    // PHY Updated
    if (param->tx_phy == BT_CONN_LE_TX_POWER_PHY_1M) {
        printk("PHY updated. New PHY: 1M\n");
    }
    else if (param->tx_phy == BT_CONN_LE_TX_POWER_PHY_2M) {
        printk("PHY updated. New PHY: 2M\n");
    }
    else if (param->tx_phy == BT_CONN_LE_TX_POWER_PHY_CODED_S8) {
        printk("PHY updated. New PHY: Long Range\n");
    }
}

void on_le_data_len_updated(struct bt_conn *conn, struct bt_conn_le_data_len_info *info)
{
    uint16_t tx_len     = info->tx_max_len; 
    uint16_t tx_time    = info->tx_max_time;
    uint16_t rx_len     = info->rx_max_len;
    uint16_t rx_time    = info->rx_max_time;
    printk("Data length updated. Length %d/%d bytes, time %d/%d us\n", tx_len, rx_len, tx_time, rx_time);
}

struct bt_conn_cb connection_callbacks = {
	.connected = on_connected,
	.disconnected = on_disconnected,
	.recycled = recycled_cb,
	.le_param_updated = on_param_updated,
	.le_phy_updated = on_le_phy_updated,
	.le_data_len_updated = on_le_data_len_updated
};

static int init_button(void)
{
	int err;

	err = dk_buttons_init(button_changed);
	if (err) {
		printk("Cannot init buttons (err: %d)\n", err);
	}

	return err;
}

int main(void)
{
	int blink_status = 0;
	int err;

	LOG_INF("Starting Lesson 4 - Exercise 2 \n");

	err = dk_leds_init();
	if (err) {
		LOG_ERR("LEDs init failed (err %d)\n", err);
		return -1;
	}

	err = init_button();
	if (err) {
		printk("Button init failed (err %d)\n", err);
		return -1;
	}

	err = bt_enable(NULL);
	if (err) {
		LOG_ERR("Bluetooth init failed (err %d)\n", err);
		return -1;
	}

	bt_conn_cb_register(&connection_callbacks);

	err = my_lbs_init(&app_callbacks);
	if (err) {
		printk("Failed to init LBS (err:%d)\n", err);
		return -1;
	}

	LOG_INF("Bluetooth initialized\n");
	k_work_init(&adv_work, adv_work_handler);
	advertising_start();

	// Käynnistetään nopea ADC
	fast_adc_init_and_start();

	for (;;) {
		dk_set_led(RUN_STATUS_LED, (++blink_status) % 2);
		k_sleep(K_MSEC(RUN_LED_BLINK_INTERVAL));
	}
}
/* STEP 18.2 - Define and initialize a thread to send data periodically */
K_THREAD_DEFINE(send_data_thread_id, STACKSIZE, send_data_thread, NULL, NULL, NULL, PRIORITY, 0, 0);