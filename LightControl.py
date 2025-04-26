# LightControl by vwall
# Supports WS2812B & SK2812 rgb + rgbw (change bpp/bites per pixel (3=rgb, 4=rgb+w))
# Works only with rgb and rgbw format. Hex code is handled in the order module
# This script uses the json_config_parser Module for configuration
# NOTE: The "type: ignore" commtents are for the vs-code micropico extension only! The main reason is that the values from the JSON-File are unknown
# NOTE: For WW/CW LEDs (24V): setting bpp = 3 is required (Byte 0=warm, 1=cold, 2=not used)

Version='6.0.3_alfa'

import utime as time
from neopixel import NeoPixel
from machine import Pin
from json_config_parser import config

class LightControl:
    def __init__(self, config_file='/params/config.json', status_file='/params/status.json'):
        self.settings = config(config_file, layers=2)
        self.status = config(status_file, layers=1)
        self.cache = self.status.get(param='color')

        self.led_pin = self.settings.get('LightControl_settings', 'led_pin')
        self.pixel = self.settings.get('LightControl_settings', 'led_qty')
        self.bpp = self.settings.get('LightControl_settings', 'bytes_per_pixel')
        self.autostart = self.settings.get('LightControl_settings', 'autostart')
        self.dim_status = self.status.get(param='dim_status')

        self.level = 0  # type: ignore
        self.led = Pin(self.led_pin, Pin.OUT, value=0)
        self.np = NeoPixel(self.led, self.pixel, bpp=self.bpp)

        if self.autostart:
            self.set_dim(self.dim_status)

    # static color (also used by dim)
    def static(self, color, level=1):
        color = list(color)
        if len(color) < 4:
            color.append(0)
        for i in range(self.pixel): # type: ignore
            self.np[i] = ( # type: ignore
                int(color[0] * level),
                int(color[1] * level),
                int(color[2] * level),
                int(color[3] * level)
            )
        self.np.write()
        self.cache = color
        return color

    def clear(self):
        for i in range(self.pixel): # type: ignore
            self.np[i] = (0, 0, 0, 0) # type: ignore
        self.np.write()

    # Dim functions
    def set_dim(self, target, speed=1):
        actual = int(self.level * 100)
        target = int(target)
        if actual == target:
            return

        if target > actual:
            self._ramp_up(actual, target, speed)
        else:
            self._ramp_down(actual, target, speed)

        self.status.save_param(param='dim_status', new_value=target)

    def _ramp_up(self, actual, target, speed):
        while actual < target:
            actual += 1
            if actual > target:
                actual = target
            self.level = actual / 100
            self.static(self.cache, self.level)
            time.sleep_ms(speed)

    def _ramp_down(self, actual, target, speed):
        while actual > target:
            actual -= 1
            if actual < target:
                actual = target
            self.level = actual / 100
            self.static(self.cache, self.level)
            time.sleep_ms(speed)
    
    # set single pixel
    def single(self, color, segment=0, light_level=None):
        if light_level is None:
            light_level = self.level
        color = list(color)
        if len(color) < 4:
            color.append(0)
        try:
            self.np[segment] = ( # type: ignore
                int(color[0] * light_level),
                int(color[1] * light_level),
                int(color[2] * light_level),
                int(color[3] * light_level)
            )
            self.np.write()
        except:
            pass

    # set color by line animation
    def line(self, color, speed=5, dir=0, gap=1, start=0):
        line = start
        color = list(color)
        if len(color) < 4:
            color.append(0)
        if dir == 0:
            while line < self.pixel: # type: ignore
                self.np[line] = ( # type: ignore
                    int(color[0] * self.level),
                    int(color[1] * self.level),
                    int(color[2] * self.level),
                    int(color[3] * self.level)
                )
                self.np.write()
                line += gap
                time.sleep_ms(speed)
        elif dir == 1:
            while line > 0:
                self.np[line] = ( # type: ignore
                    int(color[0] * self.level),
                    int(color[1] * self.level),
                    int(color[2] * self.level),
                    int(color[3] * self.level)
                )
                self.np.write()
                line -= gap
                time.sleep_ms(speed)
        self.cache = color
        self.status.save_param(param='color', new_value=color)
        return color

    def on_off(self, flag):
        saved = self.status.get(param='dim_status')
        if flag == 0:
            self.set_dim(0)
            self.status.save_param(param='dim_status', new_value=saved)
        elif flag == 1:
            self.set_dim(saved)
    
    def change_autostart(self, value):
        self.status.save_param(param='autostart', new_value=value)
    
    def change_pixel_qty(self, value):
        self.status.save_param(param='led_qty', new_value=value)

    def ret_dim(self):
        return self.status.get(param='dim_status')

LC = LightControl()     # For standalone usage

# Examples:
# LC = LightControl()
# LC.set_dim(80, 10) --> Dim to level 80% with 10ms pause between levels
# LC.line([200,0,0]) --> Set color rgb(255,0,0) by line animation