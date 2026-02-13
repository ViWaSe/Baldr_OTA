# MQTT Client Module
# New Version with separate MQTT-Handler
# There are 3 topics used, one for incoming order, one for configuration and one for the status from pico. config and status are for publishing message
# The incoming orders are processed and executed by order.py and the answer is published to the status-topic
# Settings stored in config.json

version = [7,1,5, 'a']

import utime as time
from mqtt_handler import MQTTHandler
from uWifi import Client
from json_config_parser import config
from ntp_simple import NTP
import logger
import sys
import gc
from LightControl import LC

# Connect to WLAN using PicoWifi-Module
wlan = Client()
wlan.connect()
print('[ INFO ] PicoWifi is connected!')
ntp = NTP(
    use_json_config=True,
    time_setting_file='/params/time_setting.json'
)
ok, msg = ntp.boot()
print(f'[ INFO ] {msg}')

led_onboard = Client.get_led()

# load settings from the config file
settings        = config('/params/config.json')
mqttClient      = settings.get('MQTT-config', 'Client')
mqttBroker      = settings.get('MQTT-config', 'Broker')
mqttPort        = settings.get('MQTT-config', 'Port')
mqttUser        = settings.get('MQTT-config', 'User')
mqttPW          = settings.get('MQTT-config', 'PW')
publish_in_Json = settings.get('MQTT-config', 'publish_in_json')

# Set the LED-Timer depending on the platform (pico or not)
is_pico = sys.platform == 'rp2'
if is_pico:
    led_timer=600
else:
    led_timer=400

# Create empty variables for watchdog and for the led_toggle-function
ledCount    = 0
last_msg    = time.time()
wd_counter  = 0
watchdog_last_chk = 0

mqtt = MQTTHandler(
    client_id=mqttClient,
    broker=mqttBroker,
    user=mqttUser,
    password=mqttPW,
    pinjson=publish_in_Json # type: ignore
)

event = logger.Create('Client', '/log')
wd_event = logger.Create('Watchdog', '/log', 1024)

# Watchdog-function to check the connection to the broker
def watchdog(
        watch_time=60, 
        cooldown=5,
        timeout_loops=5,
        timeout_pause=500
        ):
    global last_msg, wd_counter, watchdog_last_chk

    pico_time = time.time()
    if watchdog_last_chk and pico_time - watchdog_last_chk < cooldown:
        return True 

    if pico_time - last_msg > watch_time:
        wd_counter += 1
        wd_event.log('I', f'Counter: {wd_counter} | RTC-Time={pico_time} | Last msg={last_msg}')
        
        last_msg = pico_time 
        watchdog_last_chk = pico_time

        if wd_counter % 2 == 0:
            wd_event.log('I', f'Very quiet here. Checking connection...')
            
            # Publish the echo-message to the /status-topic and set received to false
            mqtt.publish(f'{mqttClient}/status', {"msg": "echo", "is_err_msg": False, "origin": "watchdog"})
            mqtt.set_rec(False)

            # check for answer, break if received
            for i in range (timeout_loops):
                mqtt.check_msg()
                state = mqtt.get_rec()
                if state:
                    wd_event.log('I', 'Connection still up!')
                    break
                time.sleep_ms(timeout_pause)
            
            if not state:
                wd_event.log('E', 'Message wait timeout. Probably connection lost.')
                mqtt.reconnect()
    return True

# Function for Onboard-LED as ok indicator and check connection
def led_toggle(onTime=led_timer):
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
            time.sleep(5)
            continue
        try:
            mqtt.subscribe(f'{mqttClient}/order')
        except Exception as e:
            event.log ('E', f'Failed to subscribe after successfull connect: {e}')
        
        try:
            while True:
                led_toggle()
                mqtt.check_msg()
                watchdog()
                LC.check_save()
        
        except Exception as e:
            event.log('E', f'MQTT connection lost! - {e}')
            try:
                gc.collect()
                mqtt.reconnect()
            except Exception as e:
                event.log('E', f'Failed to reconnect! [Error: {e}] Reboot...')
                import machine
                machine.reset()    