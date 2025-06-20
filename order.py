# Smarthome Order-Modul by vwall

version = '6.4.1'

import json
from LightControl import LC as LightControl
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
        
        if 'new_value' in self.data:
            new_value = self.data['new_value']
        
        if isinstance(payload, list):
            color = payload
        if isinstance(payload, str):
            try:
                color = hex_to_rgb(str(payload))
            except ValueError:
                return 'Failed! Payload is not list or hex!'
        
        if 'speed' in self.data:
            speed   = self.data['speed']
        else:
            speed = 5
        
        if 'steps' in self.data:
            steps = self.data['steps']
        else:
            steps = 50

        command_map = {
            'dim': lambda: LightControl.set_dim(payload, speed),
            'line': lambda: LightControl.line(color, speed),
            'change_autostart': lambda: LightControl.change_autostart(new_value),
            'change_pixel_qty': lambda: LightControl.change_pixel_qty(new_value),
            'smooth': lambda: LightControl.set_smooth(color, speed, steps) 
        }
        
        if command in command_map:
            command_map[command]()
            return True
        else:
            Log('Order', f'[ INFO  ]: Command not found. Command = {command}')
            return 'LC: Command not found'

    # Admin-Functions
    def admin(self):

        command = self.data['command']

        if 'new_value' in self.data:
            new_value = self.data['new_value']

        command_map = {
            'echo': lambda: 'Pico_alive',
            'alive': lambda: 'OK',
            'offline': lambda: self.handle_offline(),
            'get_version': lambda: self.get_version(),
            'change_led_qty': lambda: self.change_led_qty(new_value),
            'get_qty': lambda: LightControl.pixel,
            'set_autostart': lambda: self.change_autostart_setting(new_value),
            'get_log': lambda: self.get_log(),
            'set_GMT_wintertime': lambda: self.change_GMT_time(new_value),
            'set_GMT_offset': lambda: self.change_GMT_time(new_value),
            'get_timestamp': lambda: self.get_timestamp(),
            'reboot': lambda: self.reboot(),
            'get_sysinfo': lambda: self.get_sysinfo(),
            'onboard_led_active': lambda: self.onboard_led_active(new_value),
            'publish_in_json': lambda: self.pinjson(new_value)
        }
        
        return command_map.get(command, lambda: 'Command not found')()
    
    def pinjson(self, value: bool):
        from PicoClient import settings, publish_in_Json
        if publish_in_Json != value:
            settings.save_param(param='publish_in_json', new_value=value)
            publish_in_Json = value
        return True

    # Log when Broker is offfline
    def handle_offline(self):
        Log('MQTT', '[ INFO  ]: Broker is offline under normal conditions')
        return 'conn_lost'

    def get_sysinfo(self):
        import sys
        platform = sys.platform
        return f'Platform: {platform}'

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
    
    def onboard_led_active(self, new_state):
        from PicoWifi import led_onboard
        led_onboard.set_active(new_state)
        return 'not yet implemented. Sorry!'
    
    # Get Timestamp from NTP-Module
    def get_timestamp(self):
        from NTP import timestamp
        return timestamp()
    
    # Change NTP-Settings (Wintertime and GMT-Osffset)
    def change_GMT_time(
            self, 
            winter=True, 
            GMT_adjust=3600
            ):
        
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

    # Change LED-quantity
    def change_led_qty(self, new_value):
        LightControl.change_pixel_qty(new_value)
    
    # Change Autostart-setting
    def change_autostart_setting(self, new_value):
        LightControl.change_autostart(new_value)

    def get_log(self):
        sub = self.data['logfile']
        try:
            with open(f'{sub}.log', 'r') as f:
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

        # Get the Order-Type from JSON
        if 'sub_type' in data:
            order = data['sub_type']
        else:
            order = data['Type']
        
        order_instance = Proc(data)
        call = getattr(order_instance, order)()
        return call
    except KeyError as e:
        Log('Order', f'[ ERROR ]: Key-Error / Key not found - {e}')
        return f"Key not found: {e}"
    except AttributeError:
        Log('Order', f'[ ERROR ]: The sub-type >{order}< is not a known instance')
        return 'Command not found. Check your input!'
    except Exception as e:
        Log('Order', f'[ ERROR ]: Unknown Error - {e}')
        return f"Unknown Error: {e}"

