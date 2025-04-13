from umqtt_simple import MQTTClient
from logger import Log
import utime as time

Version = '1.0'

class MQTTHandler:
    def __init__(self, client_id, broker, user=None, password=None):
        self.client_id = client_id
        self.broker = broker
        self.user = user
        self.password = password
        self.client = None

    def connect(self):
        # Establish MQTT-Connection
        try:
            self.client = MQTTClient(self.client_id, self.broker, user=self.user, password=self.password)
            self.client.set_callback(self.on_message)
            self.client.set_last_will(topic=f"{self.client_id}/status", msg='{"msg": "offline"}', retain=True)
            self.client.connect()
            Log('MQTT', '[ INFO  ]: MQTT connection established!')
            return True
        except Exception as e:
            Log('MQTT', f'[ FAIL  ]: Connection failed - {e}')
            return False

    def on_message(self, topic, msg):
        try:
            nachricht = msg.decode('utf-8')
            Log('MQTT', f'[ INFO  ]: Received message: {nachricht}')
            
            import ujson as json
            payload = json.loads(nachricht)

            if payload.get('Type') == 'admin' and payload.get('command') == 'get_update':
                module = payload.get('module', 'main.py')   # get module name, if not included in JSON, use main.py
                url = payload.get('file_url')
                self.perform_ota_update(module, url)
                return

            from order import run
            ans = run(nachricht)
            if ans:
                self.publish(f"{self.client_id}/status", str(ans))

        except Exception as e:
            Log('MQTT', f'[ FAIL  ]: Message processing failed - {e}')

    def subscribe(self, topic):
        # Subscribe-function
        if self.client:
            self.client.subscribe(topic)
            Log('MQTT', f'[ INFO  ]: Subscribed to {topic}')

    def publish(self, topic, message, retain=False):
        # Publish-function
        if self.client:
            self.client.publish(topic, message, retain=retain)
            Log('MQTT', f'[ INFO  ]: Published message to {topic}: {message}')

    def check_msg(self):
        # Check for incoming messages, reconnect if needed
        try:
            if self.client:
                self.client.check_msg()
        except Exception as e:
            Log('MQTT', f'[ ERROR ]: MQTT error - {e}')
            self.reconnect()

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            Log('MQTT', '[ INFO  ]: MQTT connection closed')
    
    def reconnect(self):
        Log('MQTT', '[ RECONNECT ]: Attempting to reconnect...')
        self.disconnect() 
        while not self.connect(): 
            Log('MQTT', '[ RECONNECT ]: Reconnect failed, retrying in 5 seconds...')
            time.sleep(5) 
        Log('MQTT', '[ RECONNECT ]: Reconnected successfully!')
    
    # Update-function
    def perform_ota_update(self, module_name='main.py', file_url='https://github.com/ViWaSe/Baldr/blob/main/6.0.1/main.py'):
        import urequests as requests
        import os
        if '/' in module_name or '..' in module_name:
            Log('OTA', '[ FAIL  ]: Invalid module name')
            return
        try:
            Log('OTA', f'[ INFO  ]: Downloading update: {module_name}')
            response = requests.get(file_url)
            if response.status_code == 200:
                existing_content = ''
                if module_name in os.listdir():
                    with open(module_name, 'r') as f:
                        existing_content = f.read()

                if existing_content != response.text:
                    with open(module_name, "w") as f:
                        f.write(response.text)
                    Log('OTA', f'[ INFO  ]: {module_name} updated successfully')
                else:
                    Log('OTA', f'[ INFO  ]: No update needed for {module_name}')

                self.publish(f"{self.client_id}/status", f'{{"msg": "{module_name} update successful"}}')

                # Optionaler Reboot nur bei main.py
                if module_name.lower() == "main.py":
                    import machine
                    machine.reset()

            else:
                Log('OTA', f'[ FAIL  ]: Could not download {module_name}')
                self.publish(f"{self.client_id}/status", f'{{"msg": "update failed for {module_name}"}}')

        except Exception as e:
            Log('OTA', f'[ FAIL  ]: Update error - {e}')
            self.publish(f"{self.client_id}/status", f'{{"msg": "update error: {e}"}}')