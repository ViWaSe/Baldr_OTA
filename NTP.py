# Time setting via NTP-Server

Version = '1.1'

import machine
import utime as time
import usocket as socket
import ustruct as struct
from json_config_parser import config

# Load time-settings from JSON
time_setting    = config('/params/time_setting.json', layers=1)
GMT_winter      = time_setting.get(param='use_winter_time') # type: ignore
offline_time    = time_setting.get(param='offline_time') # type: ignore

def save_time(time):
    time_setting.save_param('offline_time', time)

# Winterzeit / Sommerzeit
if GMT_winter == True:
    GMT_OFFSET = 3600 * 1 # 3600 = 1 h (Winterzeit)
else:
    GMT_OFFSET = 3600 * 2 # 3600 = 1 h (Sommerzeit)

NTP_HOST = 'pool.ntp.org'

def getTimeNTP():
    NTP_DELTA = 2208988800
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(NTP_HOST, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()
    ntp_time = struct.unpack("!I", msg[40:44])[0]
    return time.gmtime(ntp_time - NTP_DELTA + GMT_OFFSET)

def setTimeRTC():
    tm = getTimeNTP()
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
    #mt = machine.RTC().datetime()
    #Log('adjusted machine Time from NTP-Server')
    #print('adjusted machine Time from NTP-Server')

def timestamp():
    try:
        setTimeRTC()
    except:
        pass
    tm = machine.RTC().datetime()
    return str(tm[0])+'-'+str(tm[1])+'-'+str(tm[2])+'|'+str(tm[4])+':'+str(tm[5])+':'+str(tm[6])

def getTimeRTC():
    setTimeRTC()
    tm = machine.RTC().datetime()
    return tm
