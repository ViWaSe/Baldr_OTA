# LightControl by vwall
# Supports WS2812B & SK2812 rgb + rgbw (change bpp/bites per pixel (3=rgb, 4=rgb+w))
# Works only with rgb and rgbw format. Hex code is handled in the order module
# This script uses the json_config_parser Module for configuration
# NOTE: The "type: ignore" commtents are for the vs-code micropico extension only! The main reason is that the values from the JSON-File are unknown
# NOTE: For WW/CW LEDs (24V): setting bpp = 3 is required (Byte 0=warm, 1=cold, 2=not used)

Version='5.3.1'

import utime as time
from neopixel import NeoPixel
from machine import Pin
from json_config_parser import config

# Load configuration from config file
settings    = config('/params/config.json', layers=2)
status      = config('/params/status.json', layers=1)
cache       = status.get(param='color')
led_pin     = settings.get('LightControl_settings','led_pin')
pixel       = settings.get('LightControl_settings','led_qty')
PixelByte   = settings.get('LightControl_settings','bytes_per_pixel')
autostart   = settings.get('LightControl_settings','autostart')

level       = 0

# Initiate LED-Pin and Neo-Pixel settings
led = Pin(led_pin, Pin.OUT, value=0)
np  = NeoPixel(led, pixel, bpp=PixelByte) # bpp = bytes per pixel # type: ignore

# Admin-Functions: ----------------------------------------------------------------------------------------------------------

# re-initiate the Pixel-value and set the dim-level again
def re_initiate_pixel():
    global pixel
    pixel       = settings.get('LightControl_settings','led_qty')
    dim_status  = status.get(param='dim_status')
    dim(dim_status).set()

# Change LED-Pin
def set_led(new_device):
    global np, status
    device          = config(new_device, layers=1)
    try:
        led_pin     = device.get(param='pin')
        new_pixel   = device.get(param='pixel')
        new_bpp     = device.get(param='bytes_per_pixel')
        led         = Pin(led_pin, Pin.OUT, value=0)
        np          = NeoPixel(led, new_pixel, bpp=new_bpp)  # type: ignore 
        # create the status variable with the JSON-File of the new device
        status      = config(new_device, layers=1)
        return 'successfully changed led-pin'
    except Exception as Argument:
        return Argument

# Restore default NeoPixel pin
def set_led_to_default():
    global led, np, status
    led = Pin(led_pin, Pin.OUT, value=0)
    np  = NeoPixel(led, pixel, bpp=PixelByte) # bpp = bytes per pixel # type: ignore
    status      = config('status.json', layers=1)

# Change LED-Quantity
def set_led_qty(new_qty):
    global settings
    settings.save_param('LightControl_settings', 'led_qty', new_qty)

# /Admin-Functions ----------------------------------------------------------------------------------------------------------


# Set all LEDs (Basic function)
def static(
        color, 
        level=1
        ):
    global pixel, cache
    color=list(color)
    if len(color)<4:
        color.append(0)
    for i in range (pixel):     # type: ignore
        np[i] = (               # type: ignore
            int(color[0]*level), 
            int(color[1]*level), 
            int(color[2]*level), 
            int(color[3]*level)
            )
    np.write()
    cache=color
    return cache

# clear all pixels
def clear():
    global pixel
    for i in range (pixel): # type: ignore 
        np[i] = (0, 0, 0, 0) # type: ignore
    np.write()

# Dim-Functions. Run it with the .set()-function.
class dim():
    def __init__(
        self, 
        target, 
        speed=1,
        level=level 
    ):
        self.target = target
        self.speed  = speed
        self.level  = level
        self.actual = self.level * 100
    
    def set(self):
        global level
        self.actual = level * 100
        if self.target < self.actual:
            self.ramp_dn()
        elif self.target > self.actual:
            self.ramp_up()
        else:
            pass
        self.save()

    def ramp_up(self):
        global level, cache
        self.actual = level * 100

        while self.actual < self.target:
            self.actual += 1
            level = self.actual/100
            if self.actual <= 1:
                static(cache, 0)
            else:
                static(cache, level)  # type: ignore
                time.sleep_ms(self.speed)

    def ramp_dn(self):
        global level, cache
        self.actual = level * 100
        
        while self.actual > self.target:
            self.actual -= 1
            level = self.actual/100
            if self.actual <= 1:
                static(cache, 0)
            else:
                static(cache, level)  # type: ignore
                time.sleep_ms(self.speed)
    
    def single(self):
        # single(cache, self.target, self.segment)
        pass 

    def save(self):
        status.save_param(param='dim_status', new_value=self.target)

# set color to a single pixel
def single(
        color,
        light_level=level, 
        segment=0
        ):
    if segment <= -1:
        color = [0,0,0,0]
    else:
        color=list(color)
    if len(color)<4:
        color.append(0)
    try:
        np[segment] = ( # type: ignore # type: ignore
            int(color[0]*light_level), 
            int(color[1]*light_level), 
            int(color[2]*light_level), 
            int(color[3]*light_level)
            )
        np.write()
    except:
        pass

# Set color with line-animation
def line(
        color, 
        speed=5, 
        dir=0, 
        gap=1, 
        start=0
        ):
    global pixel, cache
    speed = int(speed)
    line = start
    color=list(color)
    if len(color)<4:
        color.append(0)
    if dir == 0:
        while line < pixel: # type: ignore
            np[line] = ( # type: ignore
                int(color[0]*level), 
                int(color[1]*level), 
                int(color[2]*level), 
                int(color[3]*level)
                )
            np.write()
            line += gap
            time.sleep_ms(speed)        
    elif dir == 1:
        while line > 0:
            np[line] = ( # type: ignore
                int(color[0]*level), 
                int(color[1]*level), 
                int(color[2]*level), 
                int(color[3]*level)
                )
            line -= gap
            np.write()
            time.sleep_ms(speed)
    cache = color
    status.save_param(param='color', new_value=cache)
    return cache

# Under Construction:
def soft_swap(
        color=(
            0,
            0,
            0,
            0
            ), 
        speed=5
        ):
    pass

def on_off(flag):
    saved = status.get(param='dim_status')
    if flag == 0:
        dim(0).set()
        status.save_param(param='dim_status', new_value=saved)
    elif flag == 1:
        dim(saved).set()

# Load the last saved light-level
if autostart == True:
    dim_status = status.get(param='dim_status')
    dim(dim_status).set()

# Return actual light level
def ret_dim():
    level = status.get(param='dim_status')
    return level
