# Wifi network module for Prapberry pi pico and ESP-32
# configuration stored in JSON-File
# works with micropython v1.21.0 and higher
version = '6.0.1'

import utime as time
import network, rp2, machine
from json_config_parser import config
from logger import Log

# Error-Log
wlan = network.WLAN(network.STA_IF)

# Get configuration
settings    = config('/params/config.json')
rp2.country = settings.get('Wifi-config', 'country')
wlanSSID    = settings.get('Wifi-config', 'SSID')
wlanPW      = settings.get('Wifi-config', 'PW')
wlanName    = settings.get('Wifi-config', 'Hostname')

led_onboard = machine.Pin('LED', machine.Pin.OUT, value=0)

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

# Handling of WLAN-Status-Codes
def error_handling(errorno):
    return ERROR_CODES.get(errorno, 'UNKNOWN_ERROR')

# Save IP-Adress in JSON-File
def saveIP(ip):
    settings.save_param('Wifi-config', 'IP', ip)

# Flash-Funktion of Onboard-LED
def led_flash(pause=1000):
    led_onboard.on()
    time.sleep_ms(pause)
    led_onboard.off()

# Connect to the Network
def connect(max_attempts=5):
    global wlan
    network.hostname(wlanName)
    wlan.config(pm=0xa11140)
    attempts = 0
    while attempts < max_attempts:
        if not wlan.isconnected():
            Log('WIFI', f'[ INFO ]: Connecting to {wlanSSID} ...')
            wlan.active(True)
            wlan.connect(wlanSSID, wlanPW)
            while not wlan.isconnected():
                wstat = error_handling(wlan.status())
                if wstat == 'LINK_BADAUTH':
                    Log('WIFI', '[ FAIL ]: Wifi authentication failed! Probably wrong password!')
                    return
                elif wstat == 'LINK_UP':
                    break
                Log('WIFI', f'[ INFO ]: Connection status: {wstat}, retrying...')
                led_flash()
                time.sleep(1)
        if wlan.isconnected():
            led_onboard.on()
            Log('WIFI', '[ INFO ]: Connected!')
            w_status = wlan.ifconfig()
            Log('WIFI', '[ INFO ]: IP = ' + w_status[0])
            saveIP(w_status[0])
            return
        else:
            Log('WIFI', f'[ FAIL ]: Connection failed! Status: {wstat}, | retrying...')
            attempts += 1
            led_onboard.off()
            time.sleep(2)
    Log('WIFI', '[ FAIL ]: Maximum retry attempts reached. Connection failed.')

# Check Wifi connection status. If not successful, try to reconnect.
def check_status(retries=3, delay=2):
    import socket
    global wlan
    try:
        addr = socket.getaddrinfo("google.com", 80)
        Log('WIFI', '[ INFO ]: Successfully tested network connection!')
        return True
    except Exception as e:
        Log('WIFI', '[ FAIL ]: Wifi connection lost - ' + str(e))
        if retries > 0:
            Log('WIFI', '[ INFO ]: Retrying connection...')
            Log('WIFI', '[ INFO ]: Number of retries: ' + str(retries))
            time.sleep(delay)
            connect() 
            return check_status(retries - 1, delay)
        else:
            Log('WIFI', '[ FAIL ]: Failed to reconnect after several attempts.')
            return False
