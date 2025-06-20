# LightControl by vwall
# Supports WS2812B & SK2812 rgb + rgbw (change bpp/bites per pixel (3=rgb, 4=rgb+w))
# Works only with rgb and rgbw format. Hex code is handled in the order module
# This script uses the json_config_parser Module for configuration
# NOTE: The "type: ignore" commtents are for the vs-code micropico extension only! The main reason is that the values from the JSON-File are unknown
# NOTE: For WW/CW LEDs (24V): setting bpp = 3 is required (Byte 0=warm, 1=cold, 2=not used)

version='6.4.0'

import utime as time
from neopixel import NeoPixel
from machine import Pin
from json_config_parser import config
from PicoWifi import Log

try:
    from typing import Any
except ImportError:
    Any = object

class LightControl:
    def __init__(self, config_file='/params/config.json', status_file='/params/status.json'):
        self.settings   = config(config_file, layers=2)
        self.status     = config(status_file, layers=1)
        self.cache      = self.status.get(param='color')

        self.led_pin    = self.settings.get('LightControl_settings', 'led_pin')
        self.bpp        = self.settings.get('LightControl_settings', 'bytes_per_pixel')
        self.autostart  = self.settings.get('LightControl_settings', 'autostart')
        self.dim_status = self.status.get(param='dim_status')

        # Check Pixel-Value
        pixel_value     = self.settings.get('LightControl_settings', 'led_qty')
        if pixel_value is None:
            missing_pixel_error = "Missing 'led_gty' in config.json!"
            Log('LC',f' [ ERROR ]: {missing_pixel_error}')
            return missing_pixel_error
        
        self.pixel: int = int(pixel_value)

        self.level = 0
        self.led = Pin(self.led_pin, Pin.OUT, value=0)
        self.np: Any = NeoPixel(self.led, self.pixel, bpp=self.bpp) # type: ignore # type

        if self.autostart:
            self.set_dim(self.dim_status)

    # static color (also used by dim)
    def static(
            self, 
            color, 
            level=1
            ):
        color = list(color)
        while len(color) < 4:
            color.append(0)
        for i in range(self.pixel):
            self.np[i] = ( 
                int(color[0] * level),
                int(color[1] * level),
                int(color[2] * level),
                int(color[3] * level)
            )
        self.np.write()
        self.cache = color
        return color

    def clear(self):
        for i in range(self.pixel):
            self.np[i] = (0, 0, 0, 0) 
        self.np.write()

    # Dim functions
    def set_dim(
            self, 
            target, 
            speed=1
            ):
        actual = int(self.level * 100)
        target = int(target)
        if actual == target:
            return

        if target > actual:
            self._ramp_up(actual, target, speed)
        else:
            self._ramp_down(actual, target, speed)

        self.status.save_param(param='dim_status', new_value=target)

    def _ramp_up(
            self, 
            actual, 
            target, 
            speed
            ):
        while actual < target:
            actual += 1
            if actual > target:
                actual = target
            self.level = actual / 100
            self.static(self.cache, self.level)
            time.sleep_ms(speed)

    def _ramp_down(
            self, 
            actual, 
            target, 
            speed
            ):
        while actual > target:
            actual -= 1
            if actual < target:
                actual = target
            self.level = actual / 100
            self.static(self.cache, self.level)
            time.sleep_ms(speed)
    
    # set single pixel
    def single(
            self, 
            color, 
            segment=0, 
            light_level=None
            ):
        if light_level is None:
            light_level = self.level
        color = list(color)
        while len(color) < 4:
            color.append(0)
        try:
            self.np[segment] = (
                int(color[0] * light_level),
                int(color[1] * light_level),
                int(color[2] * light_level),
                int(color[3] * light_level)
            )
            self.np.write()
        except:
            pass

    # set color by line animation
    def line(
            self, 
            color, 
            speed=5, 
            dir=0, 
            gap=1, 
            start=0
            ):
        
        line = start
        color = list(color)
        while len(color) < 4:
            color.append(0)
        if dir == 0:
            while line < self.pixel: 
                self.np[line] = (
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
                self.np[line] = (
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
    
    # set Color by soft transition
    def set_smooth(
            self, 
            target_color, 
            speed=10, 
            steps=50
            ):
        
        current = list(self.cache) # type: ignore
        target = list(target_color)
        
        while len(target) < 4:
            target.append(0)
        
        for step in range(1, steps + 1):
            intermediate = [
                int(current[i] + (target[i] - current[i]) * step / steps)
                for i in range(4) 
            ]
        
            self.static(intermediate, self.level)
            time.sleep_ms(speed)
        
        self.cache = target
        self.status.save_param(param='color', new_value=target)
        return target

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