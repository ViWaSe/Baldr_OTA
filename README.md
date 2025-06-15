# uBaldr-OTA-Update
Use this repository to update your uBaldr-Device.

# How to...
To trigger an Update, send a JSON-String to the device/order-Topic with the Base-URL and the modules to update.
Example:
>{
>  "sub_type": "admin",
>  "command": "get_update",
>  "module": [
>    "main.py",
>    "PicoWifi.py",
>    "order.py"
>  ],
>  "base_url": "https://raw.githubusercontent.com/ViWaSe/Baldr_OTA/refs/heads/main/"
>}

After successfull update, the device will reboot.
