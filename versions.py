# harvest the Versions of the modules

from PicoClient import version as Client
from PicoWifi import version as Wifi
from order import version as Order
from NTP import Version as NTP
from LightControl import version as LC
from json_config_parser import version as json
from mqtt_handler import version as mqtt_handler

versions = {'Client': Client, 'Wifi': Wifi, 'Order': Order, 'NTP': NTP, 'LightControl': LC, 'json': json, 'MQTT-Handler': mqtt_handler}

def by_module(module):
    return versions[module]

def all():
    return versions

def depencies():
    pass