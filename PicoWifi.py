# Wifi network module for Prapberry pi pico and ESP-32
# configuration stored in JSON-File
# works with micropython v1.21.0 and higher
version = '6.1.4'

import utime as time
import network, machine
from json_config_parser import config
from logger import Log
import sys

# Get configuration
settings    = config('/params/config.json')
wlanSSID    = settings.get('Wifi-config', 'SSID')
wlanPW      = settings.get('Wifi-config', 'PW')
wlanName    = settings.get('Wifi-config', 'Hostname')

# check if pico is used or not
is_pico = sys.platform == 'rp2'

# Get the Broker-IP to perform later Network-check
test_host   = settings.get('MQTT-config', 'Broker')

# Create inverted-led-class for ESP32-S3
class inverted_led:
    def __init__(self, pin):
        self.led = pin
    def on(self):
        self.led.off()
    def off(self):
        self.led.on()
    def toggle(self):
        self.led.value(not self.led.value())

# If Pico, use normal settings - if not, use inverted led-setting and onboard_led from config.json
if is_pico:
    import rp2
    led_onboard = machine.Pin('LED', machine.Pin.OUT, value=0)
else:
    led_inverted = settings.get('Wifi-config', 'led_inverted')
    if led_inverted == True:
        led_onboard = inverted_led(machine.Pin(settings.get('Wifi-config', 'onboard_led'), machine.Pin.OUT))
    else:
        led_onboard = machine.Pin(settings.get('Wifi-config', 'onboard_led'), machine.Pin.OUT)

# wlan-status codes
ERROR_CODES = {
    0: 'LINK_DOWN',
    1: 'LINK_JOIN',
    2: 'LINK_NOIP',
    3: 'LINK_UP',
    -1: 'LINK_FAIL',
    -2: 'LINK_NONET',
    -3: 'LINK_BADAUTH'
}

# Ensure that wifi is ready
led_onboard.off()
time.sleep(2)
wlan = network.WLAN(network.STA_IF)

# Handling of WLAN-Status-Codes
def error_handling(errorno):
    return ERROR_CODES.get(errorno, 'UNKNOWN_ERROR')

# Save IP-Adress in JSON-File
def saveIP(ip):
    settings.save_param('Wifi-config', 'IP', ip)

# Flash-Funktion of Onboard-LED
def led_flash(on=1000, off=0):
    led_onboard.on()
    time.sleep_ms(on)
    led_onboard.off()
    time.sleep_ms(off)

# Connect to the Network with a number of max attempts
def connect(max_attempts=5):
    global wlan
    if is_pico:
        rp2.country = settings.get('Wifi-config', 'country')
        network.hostname(wlanName)
        wlan.config(pm=0xa11140)
    attempts = 0

    # Try to connect. Increase Max attempts when connection fails
    while attempts < max_attempts:
        if not wlan.isconnected():
            Log('WIFI', f'[ INFO  ]: Connecting to {wlanSSID} ...')
            wlan.active(False)
            time.sleep(0.5)
            wlan.active(True)
            wlan.connect(wlanSSID, wlanPW)
            if not wlan.isconnected():
                wstat = error_handling(wlan.status())
                if wstat == 'LINK_BADAUTH':
                    Log('WIFI', '[ FAIL ]: Wifi authentication failed! Probably wrong password!')
                    return
                elif wstat == 'LINK_UP':
                    break
                if wstat == 'LINK_JOIN':
                    Log('WIFI', f'[ INFO  ]: Connection not yet established | status: {wstat}, still trying...')
                else:
                    Log('WIFI', f'[ WARN  ]: Connection failed during startup | status: {wstat}, retrying...')
                led_flash(500, 1000)
        if wlan.isconnected():
            led_onboard.on()
            Log('WIFI', '[ INFO  ]: Connected!')
            w_status = wlan.ifconfig()
            Log('WIFI', '[ INFO  ]: IP = ' + w_status[0])
            saveIP(w_status[0])
            return
        else:
            Log('WIFI', f'[ FAIL  ]: {attempts}: Connection failed! Status: {wstat}, | retrying...')
            attempts += 1
    
    # Log failed connection after maximum retries was reached. Then reboot.
    Log('WIFI', f'[ FAIL  ]: Maximum retry attempts ({max_attempts}) reached. Connection failed.')
    Log('WIFI', '[ INFO  ]: Maybe something wrong with the wifi-chip. Will now reboot...')
    machine.reset()

# Check Wifi connection status. If not successful, try to reconnect.
def check_status(
        retries=60, 
        timeout=2
        ):
    
    import socket
    global wlan
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((test_host, 1883))
        s.close()
        Log('WIFI', '[ INFO  ]: Successfully tested network connection!')
        return True
    except Exception as e:
        Log('WIFI', '[ FAIL  ]: Wifi connection lost - ' + str(e))
        if retries > 0:
            Log('WIFI', '[ INFO  ]: Retrying connection...')
            Log('WIFI', '[ INFO  ]: Number of retries: ' + str(retries))
            retries -=1
            led_flash(on=500, off=500)
            led_flash(on=500, off=500)
            connect() 
        else:
            Log('WIFI', '[ FAIL  ]: Failed to reconnect after several attempts. Will reboot now...')
            machine.reset()
