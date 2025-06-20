# Wifi network module for Prapberry pi pico and ESP-32
# configuration stored in JSON-File
# works with micropython v1.21.0 and higher
version = '6.4.0'

import utime as time
import network, machine
from json_config_parser import config
from logger import Log
from Led_controller import LedController
import sys

# Get configuration
settings    = config('/params/config.json')
wlanSSID    = settings.get('Wifi-config', 'SSID')
wlanPW      = settings.get('Wifi-config', 'PW')
wlanName    = settings.get('Wifi-config', 'Hostname')

led_active  = settings.get('Wifi-config', 'led_active')
led_set = {
    'onboard_led': settings.get('Wifi-config', 'onboard_led'), 
    'led_inverted': settings.get('Wifi-config', 'led_inverted')
    }

# check if pico is used or not
is_pico = sys.platform == 'rp2'

# Get the Broker-IP to perform later Network-check
test_host   = settings.get('MQTT-config', 'Broker')

led_onboard = LedController(is_pico, led_set)
led_onboard.set_active(led_active) # type: ignore

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
        import rp2
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
