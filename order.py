# Smarthome Order-Modul by vwall

version = '6.2.1'

import json
from LightControl import LC
from logger import Log
from hex_to_rgb import hex_to_rgb

class Proc:
    def __init__(self, data=None):
        if data is None:
            raise ValueError("Data error.")
        self.data = data
    
    # LightControl-functions
    def LC(self):
        command = self.data['command']
        payload = self.data['payload']
        speed = self.data['speed']
        if 'format' in self.data:
            color_format = self.data['format']
            if color_format == 'hex':
                color = hex_to_rgb(str(payload)) if color_format == 'hex' else payload
            else:
                color = payload

        command_map = {
            'dim': lambda: LC.set_dim(payload, speed),
            'line': lambda: LC.line(color, speed),
            'change_autostart': lambda: LC.change_autostart(self.data['new_value']),
            'change_pixel_qty': lambda: LC.change_pixel_qty(self.data['new_value'])
        }
        
        if command in command_map:
            command_map[command]()
            # Log('Order', f'[ INFO  ]: Order sucessful. Command = {command}')
            return True
        else:
            Log('Order', f'[ INFO  ]: Command not found. Command = {command}')
            return 'LC: Command not found'

    # Admin-Functions
    def admin(self):

        command = self.data['command']
        
        command_map = {
            'echo': lambda: 'alive',
            'offline': lambda: self.handle_offline(),
            'get_version': lambda: self.get_version(),
            'change_qty': lambda: self.change_qty(),
            'get_qty': lambda: LC.pixel,
            'set_autostart': lambda: self.change_autostart_setting(),
            'get_log': lambda: self.get_log(self.data['logfile']),
            'set_GMT_wintertime': lambda: self.change_GMT_time(winter=self.data['new_value']),
            'set_GMT_offset': lambda: self.change_GMT_time(GMT_adjust=self.data['new_value']),
            'get_timestamp': lambda: self.get_timestamp(),
            'reboot': lambda: self.reboot()
        }
        
        return command_map.get(command, lambda: 'Command not found')()
    
    # Log when Broker is offfline
    def handle_offline(self):
        Log('MQTT', '[ INFO  ]: Broker is offline under normal conditions')
        return 'conn_lost'

    # Reboot-request
    def reboot(self):
        try: 
            pw = self.data['password']
        except:
            return 'No password in JSON. Try >loki<!'
        if pw == 'loki':
            import machine
            machine.reset()
        else:
            return 'Wrong password. Try >loki<!'
    # Get Timestamp from NTP-Module
    def get_timestamp(self):
        from NTP import timestamp
        return timestamp()
    
    # Change NTP-Settings (Wintertime and GMT-Osffset)
    def change_GMT_time(self, winter=True, GMT_adjust=3600):
        from json_config_parser import config
        time_setting    = config('/params/time_setting.json', layers=1)
        use_winter_time = time_setting.get(param='use_winter_time')
        GMT_offset      = time_setting.get(param='GMT_offset')
        
        if winter != use_winter_time:
            time_setting.save_param(param='use_winter_time', new_value=winter)
            Log('NTP', f'[ INFO  ]: Changed Wintertime to {winter}')
            return f'set wintertime to {winter}. Changes will take affect after reboot'
        if GMT_adjust != GMT_offset:
            time_setting.save_param('GMT_offset', GMT_adjust)
            Log('NTP', f'[ INFO  ]: Adjusted GMT-Offset to {GMT_adjust}')
            return f'set GMT-Offset to {GMT_adjust}. Changes will take affect after reboot'

    def get_version(self):
        import versions
        if self.data['sub_system'] == 'all':
            return versions.all()
        else:
            return versions.by_module(self.data['sub_system']) # type: ignore

    def change_qty(self):
        pass
    
    def change_autostart_setting(self):
        pass

    def get_log(self, sub):
        try:
            with open(sub, 'r') as f:
                cont = f.read()
                if not cont:
                    return 'Logfile is empty!'
                return cont
        except Exception as e:
            return f'Error reading Logfile: {e}'

# Run a JSON-String
def run(json_string):
    try:
        data = json.loads(json_string)

        # Messager-version check
        if 'messager_version' in data:
            version = data['messager_version']
            if version == "1.2": 
                order = data['sub_type']
            else:
                order = data['Type']
        else:
            order = data['Type']
        
        order_instance = Proc(data)
        call = getattr(order_instance, order)()
        return call
    except KeyError as e:
        Log('Order', f'[ ERROR ]: Key-Error / Key not found - {e}')
        return f"Key not found: {e}"
    except AttributeError:
        Log('Order', f'[ ERROR ]: Command not found')
        return 'Command not found. Check your input!'
    except Exception as e:
        Log('Order', f'[ ERROR ]: Unknown Error - {e}')
        return f"Unknown Error: {e}"

