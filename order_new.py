# Smarthome Order-Modul by vwall

version = '6.0.1'

import json
from LightControl import LightControl
from logger import Log
from hex_to_rgb import hex_to_rgb

# TODO: Command Map testen | Error-Handling und logging testen

class Proc:
    def __init__(self, data=None):
        if data is None:
            raise ValueError("Es müssen gültige Daten übergeben werden.")
        self.data = data
    
    def LC(self):
        command = self.data['command']
        payload = self.data['payload']
        speed = self.data['speed']
        color_format = self.data['format']
        LC = LightControl()

        color = hex_to_rgb(str(payload)) if color_format == 'hex' else payload
        
        """
        try:
            LC.set_led(new_device=self.data['device']) 
        except KeyError:
            Log('Order', '[ ERROR  ]: No device is set. Order passed')
        except Exception as e:
            Log(f'Order', '[ ERROR  ]: Error during LED-change {e}')
        """
        command_map = {
            'dim': lambda: LC.set_dim(payload),
            'line': lambda: LC.line(color, speed),
            'on_off': lambda: LC.on_off(payload)
        }
        
        if command in command_map:
            command_map[command]()
            Log('Order', f'[ INFO  ]: Order sucessful. Command = {command}')
            return True
        else:
            Log('Order', f'[ INFO  ]: Command not found. Command = {command}')
            return 'LC: Command not found'

    def admin(self):
        LC = LightControl()
        command = self.data['command']
        
        command_map = {
            'echo': lambda: 'alive',
            'offline': lambda: self.handle_offline(),
            'get_version': lambda: self.get_version(),
            'change_qty': lambda: self.change_qty(),
            'get_qty': lambda: LC.pixel,
            'set_autostart': lambda: self.change_autostart_setting()
        }
        
        return command_map.get(command, lambda: 'Command not found')()
    
    def handle_offline(self):
        Log('MQTT', '[ INFO  ]: Broker is offline under normal conditions')
        return 'conn_lost'


    def get_version(self):
        from PicoClient import version
        if self.data['sub_system'] == 'all':
            return version
        else:
            return version.get(self.data['sub_system'], 'Version nicht gefunden.') # type: ignore

    def change_qty(self):
        LC = LightControl()
        LC.set_led_qty(self.data['new'])
        Log('LC', f'[ INFO  ]: LED-Qty changed to {self.data["new"]}')
        return 'OK'
    
    def change_autostart_setting(self):
        LC = LightControl()
        LC.set_autostart_state(self.data['new'])
        Log('LC', f'[ INFO  ]: Autostart flag changed to {self.data["new"]}')
        pass

def run(json_string):
    try:
        data = json.loads(json_string)

        # Messager-version check
        if 'messager_version' in data:
            version = data['messager_version']
            if float(version) == "1.2": 
                order = data['sub_type']
            else:
                order = data['Type']
        else:
            order = data['Type']
        
        order_instance = Proc(data)
        call = getattr(order_instance, order)()
        return call
    # TODO: Checken, ob JSONDecodeError funktioniert bzw. existiert!
    except json.JSONDecodeError: # type: ignore
        Log('Order', '[ ERROR  ]: JSON-Format-Error')
        return 'Ungültiges JSON-Format.'
    except KeyError as e:
        Log('Order', f'[ ERROR ]: Key-Error / Key not found - {e}')
        return f"Key not found: {e}"
    except AttributeError:
        Log('Order', f'[ ERROR ]: Command not found')
        return 'Command not found. Check your input!'
    except Exception as e:
        Log('Order', f'[ ERROR ]: Unknown Error - {e}')
        return f"Unknown Error: {e}"