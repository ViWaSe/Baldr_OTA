# Logger for Issues in the Baldr-Software
# NOTE: This is the first Version of this program
version = '0.2.1'

import NTP
import os

ntp_time    = NTP.timestamp()

# Check and clear logfile
def check_and_clear_log(log_file, max_size):
    global version
    size = os.stat(log_file)[6]  # Check file size
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
    check_and_clear_log(log_file=sub_file, max_size=max_size)
    time = NTP.timestamp()
    with open(sub_file, 'a') as file:
        file.write(str(time) + ' >>> ' + str(issue) + '\n')
