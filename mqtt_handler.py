# New MQTT-Handler Module for Baldr V6.x

version = '1.4.1'

from umqtt_simple import MQTTClient
from logger import Log
import utime as time
import json

# If typing don't exist:
try:
    from typing import Optional, Any
except ImportError:
    Optional = Any = object

class MQTTHandler:
    def __init__(
            self, 
            client_id, 
            broker, 
            user=None, 
            password=None,
            pinjson=False
            ):
        
        self.client_id = client_id
        self.broker = broker
        self.user = user
        self.password = password
        self.client: Optional[MQTTClient] = None # type: ignore
        self.subscribed_topic = None
        self.injson = pinjson
        self.received = False

    # Establish MQTT-Connection
    def connect(self):
        try:
            self.client = MQTTClient(self.client_id, self.broker, user=self.user, password=self.password)
            self.client.set_callback(self.on_message)
            self.client.set_last_will(topic=f"{self.client_id}/status", msg='offline', retain=True)
            self.client.connect()
            Log('MQTT', '[ INFO  ]: MQTT connection established!')
            return True
        except Exception as e:
            Log('MQTT', f'[ FAIL  ]: Connection failed - {e}')
            return False

    # process incomming messages
    def on_message(
            self, 
            topic, 
            msg
            ):
        if not msg:
            pass
        try:
            in_message = msg.decode('utf-8')
            self.set_rec(True)
            import ujson as json
            payload = json.loads(in_message)

            if payload.get('sub_type') == 'admin' and payload.get('command') == 'get_update':
                modules = payload.get('module') 
                base_url = payload.get('base_url')
                self.perform_ota_update(modules, base_url)
                return

            from order import run
            ans = run(in_message)
            
            if ans:
                if ans == 'conn_lost':
                    self.reconnect()
                else:
                    self.publish(f"{self.client_id}/status", ans)
            if not ans:
                ans = '>> No order processing <<'

        except Exception as e:
            Log('MQTT', f'[ FAIL  ]: Message processing failed - {e}')
            Log('MQTT', f'[ INFO  ]: Message: {msg} | Order result: {ans}')

    # Subscribe to the topic
    def subscribe(self, topic):
        self.subscribed_topic = topic
        if self.client:
            self.client.subscribe(topic)
            Log('MQTT', f'[ INFO  ]: Subscribed to {topic}')
            self.publish(f"{self.client_id}/status", {"msg": "online", "is_err_msg": False, "origin": "mqtt_handler"})

    # Publish-function
    def publish(
            self, 
            topic, 
            message, 
            retain=False
            ):
        if not self.client:
            return
        if self.injson:
            payload = {
                "msg": message.get("msg"),
                "is_err_msg": message.get("is_err_msg"),
                "origin": message.get("origin")
            }
            self.client.publish(topic, json.dumps(payload), retain=retain)
        else:
            self.client.publish(topic, str(message.get("msg")), retain=retain)
            # Log('MQTT', f'[ INFO  ]: Published message to {topic}: {message}')

    # Check for incoming messages, reconnect if needed
    def check_msg(self):
        try:
            if self.client:
                self.client.check_msg()
        except Exception as e:
            Log('MQTT', f'[ ERROR ]: MQTT error - {e}')
            self.reconnect()
    def wait_msg(self):
        if self.client is not None:
            self.client.wait_msg() 

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            Log('MQTT', '[ INFO  ]: MQTT connection closed')
    
    def reconnect(self):
        Log('MQTT', '[ INFO  ]: Attempting to reconnect...')
        self.disconnect() 
        while not self.connect(): 
            Log('MQTT', '[ INFO  ]: Reconnect failed, retrying in 5 seconds...')
            time.sleep(5) 
        Log('MQTT', '[ INFO  ]: Reconnected successfully!')
        self.subscribe(self.subscribed_topic)
    
    def set_rec(self, state):
        self.received=state
    def get_rec(self):
        return self.received
    def set_publish_in_json(self, state):
        self.injson = state
    
    # Update-function
    def perform_ota_update(
            self, 
            module_name='all', 
            base_url='BASE_URL'
            ):
        import urequests as requests
        import os

        if module_name == 'all':
            module_name = [
                'main.py',
                'LightControl.py',
                'PicoClient.py',
                'PicoWifi.py',
                'mqtt_handler.py',
                'order.py',
                'logger.py',
                'Led_controller.py',
                'json_config_parder.py',
                'NTP.py',
                'versions.py'
                ]

        def update_single_module(name, url):
            try:
                Log('OTA', f'[ INFO  ]: Downloading {name} from {url}')
                response = requests.get(url)
                if response.status_code == 200:
                    with open(name, "w") as f:
                        f.write(response.text)
                    Log('OTA', f'[ INFO  ]: {name} updated successfully')
                    self.publish(f"{self.client_id}/status", {"msg": f'{name} update was successful!', "is_err_msg": False, "origin": "OTA_Update"})
                else:
                    Log('OTA', f'[ FAIL  ]: Could not download {name}')
                    self.publish(f"{self.client_id}/status", {"msg": f'update failed for {name}', "is_err_msg": True, "origin": "OTA_Update"})
            except Exception as e:
                Log('OTA', f'[ FAIL  ]: Update failed for {name} - {e}')
                self.publish(f"{self.client_id}/status", {"msg": f'update error for {name}: {e}', "is_err_msg": True, "origin": "OTA_Update"})

        if isinstance(module_name, list):
            for mod in module_name:
                url = base_url + mod
                update_single_module(mod, url)
            
            self.publish(f"{self.client_id}/status", {"msg": "OTA-Update done! Will now reboot...", "is_err_msg": False, "origin": "OTA_Update"})       
            Log('OTA', '[ INFO  ]: Update done. Will now reboot ...')
            import machine
            machine.reset()
        
        else:
            self.publish(f"{self.client_id}/status", {"msg": "No module updated. Please send the modules in list-format! Try the provided string from github.", "is_err_msg": True, "origin": "OTA_Update"})
