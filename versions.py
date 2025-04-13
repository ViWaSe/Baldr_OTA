# harvest the Versions of the modules

from PicoClient import Version as Client
from PicoWifi import version as Wifi
from order import Version as Order
from NTP import Version as NTP
from LightControl import Version as LC
from json_config_parser import version as json
from switch import Version as dev_control

Versions = {'Client': Client, 'Wifi': Wifi, 'Order': Order, 'NTP': NTP, 'LightControl': LC, 'json': json, 'dev_control': dev_control}

def by_module(module):
    return Versions[module]

def all():
    return Versions

