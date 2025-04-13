# LightControl by vwall
# Supports WS2812B & SK2812 rgb + rgbw (change bpp/bites per pixel (3=rgb, 4=rgb+w))
# Works only with rgb and rgbw format. Hex code is handled in the order module
# This script uses the json_config_parser Module for configuration
# NOTE: The "type: ignore" commtents are for the vs-code micropico extension only! The main reason is that the values from the JSON-File are unknown
# NOTE: For WW/CW LEDs (24V): setting bpp = 3 is required (Byte 0=warm, 1=cold, 2=not used)

Version='6.0.1'

import utime as time
from neopixel import NeoPixel
from machine import Pin
from json_config_parser import config

class LightControl:
    def __init__(self):
        # Load configuration from JSON files
        self.settings = config('/params/config.json', layers=2)
        self.status = config('/params/status.json', layers=1)
        self.cache = self.status.get(param='color')
        
        # Initial LED parameters
        self.led_pin = self.settings.get('LightControl_settings', 'led_pin')
        self.pixel = self.settings.get('LightControl_settings', 'led_qty')
        self.PixelByte = self.settings.get('LightControl_settings', 'bytes_per_pixel')
        self.autostart = self.settings.get('LightControl_settings', 'autostart')
        self.level = 0

        # Initialize LED Pin and NeoPixel settings
        self.led = Pin(self.led_pin, Pin.OUT, value=0)
        self.np = NeoPixel(self.led, self.pixel, bpp=self.PixelByte)

        # Auto start sequence
        if self.autostart:
            self.dim_status = self.status.get(param='dim_status')
            self.set_dim(self.dim_status)

    # Helper function to set the color for a pixel
    def set_pixel_color(self, pixel, color, light_level):
        color = list(color)
        if len(color) < 4:
            color.append(0)
        return tuple(int(c * light_level) for c in color)

    # Set static color on all LEDs
    def static(self, color, level=1):
        color = list(color)
        if len(color) < 4:
            color.append(0)
        for i in range(self.pixel): # type: ignore
            self.np[i] = self.set_pixel_color(self.np[i], color, level) # type: ignore
        self.np.write()
        self.cache = color
        return self.cache

    # Clear all LEDs (set to off)
    def clear(self):
        self.np.fill((0, 0, 0, 0))
        self.np.write()

    # Dimmer class to manage dimming behavior
    class Dimmer:
        def __init__(self, target, speed=1):
            self.target = target
            self.speed = speed
            self.actual = 0

        def set(self, light_control):
            self.actual = light_control.level * 100
            if self.target < self.actual:
                self.ramp_down(light_control)
            elif self.target > self.actual:
                self.ramp_up(light_control)

        def ramp_up(self, light_control):
            while self.actual < self.target:
                self.actual += 1
                light_control.level = self.actual / 100
                light_control.static(light_control.cache, light_control.level)
                time.sleep_ms(self.speed)

        def ramp_down(self, light_control):
            while self.actual > self.target:
                self.actual -= 1
                light_control.level = self.actual / 100
                light_control.static(light_control.cache, light_control.level)
                time.sleep_ms(self.speed)

    # Change the LED configuration (pin, quantity, bytes per pixel)
    def set_led(self, new_device):
        try:
            device = config(new_device, layers=1)
            led_pin = device.get(param='pin')
            new_pixel = device.get(param='pixel')
            new_bpp = device.get(param='bytes_per_pixel')
            self.led = Pin(led_pin, Pin.OUT, value=0)
            self.np = NeoPixel(self.led, new_pixel, bpp=new_bpp)
            self.status = config(new_device, layers=1)
            return 'Successfully changed LED configuration'
        except Exception as e:
            return f"Error: {e}"

    # Set the LED quantity
    def set_led_qty(self, new_qty):
        self.settings.save_param('LightControl_settings', 'led_qty', new_qty)

    # Set the brightness level (dimming)
    def set_dim(self, target):
        dimmer = self.Dimmer(target)
        dimmer.set(self)

    # Restore the default LED configuration
    def set_led_to_default(self):
        self.led = Pin(self.led_pin, Pin.OUT, value=0)
        self.np = NeoPixel(self.led, self.pixel, bpp=self.PixelByte)
        self.status = config('status.json', layers=1)

    # Set color for a single pixel
    def single(self, color, light_level=None, segment=0):
        if light_level is None:
            light_level = self.level
        color = self.set_pixel_color(segment, color, light_level)
        self.np[segment] = color # type: ignore
        self.np.write()

    # Set a line of LEDs to a color
    def line(self, color, speed=5, dir=0, gap=1, start=0):
        line = start
        color = list(color)
        if len(color) < 4:
            color.append(0)
        if dir == 0:
            while line < self.pixel: # type: ignore
                self.np[line] = self.set_pixel_color(self.np[line], color, self.level) # type: ignore
                self.np.write()
                line += gap
                time.sleep_ms(speed)
        elif dir == 1:
            while line > 0:
                self.np[line] = self.set_pixel_color(self.np[line], color, self.level) # type: ignore
                line -= gap
                self.np.write()
                time.sleep_ms(speed)
        self.cache = color
        self.status.save_param(param='color', new_value=self.cache)
        return self.cache

    # Turn LEDs on or off
    def on_off(self, flag):
        saved = self.status.get(param='dim_status')
        if flag == 0:
            self.set_dim(0)
            self.status.save_param(param='dim_status', new_value=saved)
        elif flag == 1:
            self.set_dim(saved)

# Example of usage
# light_control = LightControl()
# light_control.static([255, 0, 0], level=0.5)
# light_control.set_dim(80)  # Set brightness level to 80%