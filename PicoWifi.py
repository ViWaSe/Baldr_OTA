# Wifi network module for Prapberry pi pico and ESP-32
# configuration stored in JSON-File
# works with micropython v1.21.0 and higher
version = '6.0.3'

import utime as time
import network, rp2, machine
from json_config_parser import config
from logger import Log

# Ensure that wifi is ready
time.sleep(2)
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

# Connect to the Network with a number of max attempts
def connect(max_attempts=5):
    global wlan
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
                Log('WIFI', f'[ INFO  ]: Connection not yet established | status: {wstat}, retrying...')
                led_flash()
                time.sleep(1)
        if wlan.isconnected():
            led_onboard.on()
            Log('WIFI', '[ INFO  ]: Connected!')
            w_status = wlan.ifconfig()
            Log('WIFI', '[ INFO ]: IP = ' + w_status[0])
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
def check_status(retries=60, delay=2):
    import socket
    global wlan
    try:
        addr = socket.getaddrinfo("google.com", 80)
        Log('WIFI', '[ INFO  ]: Successfully tested network connection!')
        return True
    except Exception as e:
        Log('WIFI', '[ FAIL  ]: Wifi connection lost - ' + str(e))
        if retries > 0:
            Log('WIFI', '[ INFO  ]: Retrying connection...')
            Log('WIFI', '[ INFO  ]: Number of retries: ' + str(retries))
            time.sleep(delay)
            retries -=1
            connect() 
        else:
            Log('WIFI', '[ FAIL  ]: Failed to reconnect after several attempts. Will reboot now...')
            machine.reset()
