# Simple script to start the Device
version = '6.1.1'

# add subdirectories to path
import PicoWifi as wlan
import PicoClient as MQTT
import LightControl

# start Light-Control
print('[ INFO ] Welcome to BALDR Version', version)

# Connect to WLAN using PicoWifi-Module
wlan.connect()
print('[ INFO ] PicoWifi is connected!')

# Establish MQTT-Connection 
print('[ INFO ] PicoClient is running!')
MQTT.go()