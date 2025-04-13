# Config-Parser for .json config files
# Currently 1 and 2 layers are supported, 2 means that the file is structured like >>>{"Example-Group": [{"example param": "example string"], "example-Group 2": [{"Example int-data": 2, ...<<<
# To parse a json-file, create a config()-Object and get the data you want with the get()-function. (t.ex example=config(file='example.json', layers=2) ==> example.get('group', 'param'))
# Use the save-param()-function to save or update data the same way as getting it with the get()-function (t.ex. example.save_param('group', 'param', 'new value'))
version = '2.1'

import json
import sys

# Add /params directory
sys.path.insert(0, "./params")

class config(object):
    
    def __init__(
            self, 
            file='config.json', 
            layers=2
    ):
        self.file   = file
        self.layers = layers

        with open(self.file) as f:
            self.conf = json.load(f)
    
# get data by the original name in the json-file   
    def get(
            self, 
            group=None, 
            param=None
    ):
        if self.layers==1:
            return self.conf[param]
        elif self.layers==2:
            section = self.conf[group]
            setting = section[0]
            par = setting[param]
            return par

# Save / update parameter with a new value
    def save_param(
            self, 
            group=None, 
            param=None, 
            new_value=None
    ):
        if self.layers == 1:
            self.conf[param] = new_value
        elif self.layers == 2:
            section = self.conf[group]
            setting = section[0]
            setting[param] = new_value

        with open(self.file, 'w') as file:
            json.dump(self.conf, file)

# Save a python-lib to a json-file (or create a new file)
    def save_lib(self, lib, filename):
        with open(filename, 'w') as f:
            json.dump(lib, f)
    
def create(filename, content):
    newfile = open(filename, 'w')
    newfile.write(content)
    newfile.close()

