# Logger for Issues in the Baldr-Software

version = '1.3.2'

import NTP
import os

ntp_time    = NTP.timestamp()

# Check size of the logfole. If it reaches 'max_size', delete the content
def check_and_clear_log(log_file, max_size):
    global version
    
    size = os.stat(log_file)[6] 
    if size > max_size:
        with open(log_file, 'w') as f:
            f.write('***   LOGGER V '+ str(version)+' | File='+str(log_file)+'   ***')
        
# Log-function. can be imported and used in all other programs
def Log(
        sub='Pico', 
        issue=None,
        dir='/log/',
        max_size=4096
        ):
    
    sub_file = dir + sub + '.log'
    time = NTP.timestamp()
    with open(sub_file, 'a') as file:
        file.write(str(time) + ' >>> ' + str(issue) + '\n')
    
    # Check and / or clear logfile
    check_and_clear_log(log_file=sub_file, max_size=max_size)

# return logfile content 
def get_log(sub, dir='/log'):
    sub_file = dir + sub + '.log'
    return sub_file
