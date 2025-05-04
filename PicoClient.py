# MQTT Client Module
# New Version with separate MQTT-Handler
# There are 3 topics used, one for incoming order, one for configuration and one for the status from pico. config and status are for publishing message
# The incoming orders are processed and executed by order.py and the answer is published to the status-topic
# Settings stored in config.json

version = '6.0.3-wd'

import utime as time # type: ignore
from mqtt_handler import MQTTHandler
from PicoWifi import led_onboard, check_status
from json_config_parser import config
from logger import Log

# load settings from the config file
settings        = config('/params/config.json')
mqttClient      = settings.get('MQTT-config', 'Client')
mqttBroker      = settings.get('MQTT-config', 'Broker')
mqttPort        = settings.get('MQTT-config', 'Port')
mqttUser        = settings.get('MQTT-config', 'User')
mqttPW          = settings.get('MQTT-config', 'PW')

# Create empty variables for watchdog and for the led_toggle-function
ledCount    = 0
last_msg    = time.time()
wd_counter  = 0
watchdog_last_chk = 0

mqtt = MQTTHandler(
    client_id=mqttClient,
    broker=mqttBroker,
    user=mqttUser,
    password=mqttPW
)

def watchdog(watch_time=1800, cooldown=5):
    global last_msg, wd_counter, watchdog_last_chk
    pico_time = time.time()
    if watchdog_last_chk and pico_time - watchdog_last_chk < cooldown:
        return True 

    if pico_time - last_msg > watch_time:
        wd_counter += 1
        Log('Watchdog', '[ CHECK ]: Very quiet here. Checking connection...')
        Log('Watchdog', f'[ INFO  ]: RTC-Time={pico_time} | Last msg={last_msg}')
        
        last_msg = pico_time 
        watchdog_last_chk = pico_time

        mqtt.publish(f'{mqttClient}/status', 'network-check performed')

        if wd_counter % 2 == 0:
            Log('Watchdog', '[ CHECK ]: Checking network...')
            if not check_status():
                Log('Watchdog', '[ FAIL ]: No Connection to Wifi. See Wifi.log for details!')
                return False
    return True

# Function for Onboard-LED as ok indicator and check connection
def led_toggle(onTime=800):
    global ledCount
    ledCount +=1
    time.sleep_ms(1)
    if ledCount >= onTime:
        led_onboard.off()
        time.sleep_ms(100)
        led_onboard.on()
        ledCount = 0
    
# Main - just call go() to start the Loop
def go():
    while True:
        if not mqtt.connect():
            Log('MQTT', '[ ERROR ]: MQTT connection failed! Retrying in 5 seconds...')
            time.sleep(5)
            continue

        mqtt.subscribe(f'{mqttClient}/order')
        Log('MQTT', '[ INFO  ]: MQTT connected, listening for messages...')
        
        try:
            while True:
                led_toggle()
                mqtt.check_msg()
                watchdog()
        
        except Exception as e:
            Log('MQTT', f'[ FAIL ]: MQTT connection lost! - {e}')
            mqtt.reconnect()
    