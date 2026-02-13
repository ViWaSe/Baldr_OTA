# LightControl by vwall
# Supports WS2812B & SK2812 rgb + rgbw (change bpp/bites per pixel (3=rgb, 4=rgb+w))
# Works only with rgb and rgbw format. Hex code is handled in the order module
# This script uses the json_config_parser Module for configuration
# NOTE: The "type: ignore" commtents are for the vs-code micropico extension only! The main reason is that the values from the JSON-File are unknown
# NOTE: For WW/CW LEDs (24V): setting bpp = 3 is required (Byte 0=warm, 1=cold, 2=not used)

version=[7,2,1]

import utime as time
from neopixel import NeoPixel
from machine import Pin
from json_config_parser import config
import logger

try:
    from typing import Any
except ImportError:
    Any = object

class LightControl:
    def __init__(
            self,
            use_config_json=True, 
            config_file='/params/config.json', 
            status_file='/params/status.json',
            logging=True,
            led_pin=15,
            bpp=3,
            pixel_pty=12,
            autostart=True
            ):
        
        """
        Parameters:
            use_config_json (bool): True, if a JSON file is used for settings. Must have 2 layers. The json_config_parser is needed.
            config_file (str): Location of the configuration-file.
            status_file (str): Location of the status-file, where level and color will be saved.
            logging (bool): Events are logged in the /log/ directory
            led_pin (int): Neopixel LED-Pin.
            bpp (int): Bytes per pixel value. 3=RGB, 4=RGBW
            pixel_pty (int): The Number of LEDs that are adressed.
            autostart (bool): Load the last color- and dim- setting from the status.json file.

        Methods:
        --------
            static(): sets all pixels at the same time.
            line(): sets pixels by line-animation
            set_smooth(): sets pixels by a smooth transition
            set_dim(): sets a dimmer-level
            change_autostart(): sets the autostart-state. If true, the pixels will be set to the last known state when power on
            change_pixel_qty(): changes the pixel-quantity
            ret_dim(self): returns the actual light level
        """

        if use_config_json:
            self.settings   = config(config_file, layers=2)
            self.led_pin    = self.settings.get('LightControl_settings', 'led_pin')
            self.bpp        = self.settings.get('LightControl_settings', 'bytes_per_pixel')
            self.autostart  = self.settings.get('LightControl_settings', 'autostart')
            self.pixel_qty  = self.settings.get('LightControl_settings', 'led_qty')
        else:
            self.led_pin    = led_pin
            self.bpp        = bpp
            self.pixel_qty  = pixel_pty
            self.autostart  = autostart

        self.status     = config(status_file, layers=1)
        self.cache      = self.status.get(param='color')
        self.dim_status = self.status.get(param='dim_status')

        if logging:
            self.event = logger.Create('LightControl', '/log')
        else:
            self.event = logger.DummyLogger()

        # Check Pixel-Value
        if self.pixel_qty is None:
            missing_pixel_error = "Missing 'led_gty' in config.json!"
            self.event.log('E', f'Initialization failed! - {missing_pixel_error}')
            return missing_pixel_error
        
        self.pixel: int = int(self.pixel_qty)

        self.level = 0
        self.led = Pin(self.led_pin, Pin.OUT, value=0)
        self.np: Any = NeoPixel(self.led, self.pixel, bpp=self.bpp) # type: ignore # type

        # Set save-timer
        self.last_change = 0
        self.need_save = False

        if self.autostart:
            self.set_dim(self.dim_status)

    # static color (also used by dim)
    def static(
            self, 
            color, 
            level_255=None
            ):
        while len(color) < 4:
            color.append(0)
        
        if level_255 is None:
            level_255 = int(self.level * 255)
        dimmed_color = tuple((c * level_255) // 255 for c in color[:4])

        for i in range(self.pixel):
            self.np[i] = dimmed_color
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
            speed=1,
            steps=2
            ):
        
        """
        Dims the LED-levels in a smooth animation.

        Parameter:
            target (int): Target-Level. Values from 0-100.
            speed (int): Pause between the 1%-steps in ms.
        """

        actual = int(self.level * 100)
        target = int(target)
        if actual == target:
            return

        if target > actual:
            self._ramp_up(actual, target, speed, steps)
        else:
            self._ramp_down(actual, target, speed, steps)

        self.last_change = time.time()
        self.needs_save = True
        return True

    def _ramp_up(
            self, 
            actual, 
            target, 
            speed,
            steps=2
            ):
        while actual < target:
            actual += steps
            if actual > target:
                actual = target
            self.level = actual / 100
            self.static(self.cache, self.level)
            time.sleep_ms(speed)

    def _ramp_down(
            self, 
            actual, 
            target, 
            speed,
            steps=2
            ):
        while actual > target:
            actual -= steps
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
        except IndexError:
            pass

    # set color by line animation
    def line(
            self, 
            color, 
            speed=5, 
            dir=0, 
            gap=1, 
            start=0,
            ):
        
        """
        Sets the color by a line-animation.

        Parameter:
            color (list): Target-color in rgbw-list-format. A list with 4 objects is expected (e.g. [255,0,0,0]).
            speed (int): Pause between the steps in ms.
            dir (int): Direction of the line. 1=forward, 2=backwards.
            gap (int): Gap betwen the leds in the animation. 1=no gap.
            start (int): start of the animation. 0=start on the first led.
        """
        
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
        self.last_change = time.time()
        self.needs_save = True
        return color
    
    # set Color by soft transition
    def set_smooth(
            self, 
            target_color, 
            speed=10, 
            steps=50
            ):
        
        """
        Change the color by smooth transition.
        
        Parameters:
            target_color(list): A list with 4 integer objects with the color-value (R,G,B,W | 0...255). At least one value is needed. If one is missing (i.e. W), only the given colors are set (255,255 -> 255,255,0,0).
            speed(int): Pause between steps in ms. 10 is default.
            steps(int): Transition steps between pause. 50 is recommended to run a smooth animation.
            """
        
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
        self.last_change = time.time()
        self.needs_save = True
        return target

    def change_autostart(self, value):
        self.status.save_param(param='autostart', new_value=value)
    
    def change_pixel_qty(self, value):
        self.status.save_param(param='led_qty', new_value=value)
    
    def get_info(self):
        return {"version": version, "led_qty": self.pixel_qty, "led_pin": self.led_pin, "color": self.cache, "light_level": self.dim_status}
    
    def check_save(self, force=False):
        if force or (self.need_save and (time.time() - self.last_change) > 5):
            self.status.save_param(param='color', new_value=self.cache)
            self.status.save_param(param='dim_status', new_value=int(self.level * 100))
            self.need_save = False

# Auto-initialize LEDs
LC = LightControl()

"""
def set_smooth(self, target_color, speed=10, steps=50):
    current = list(self.cache)
    target = list(target_color)
    while len(target) < 4: target.append(0)
    
    # Vorbereiten der Differenzen spart Rechenzeit in der Schleife
    diffs = [target[i] - current[i] for i in range(4)]
    
    for step in range(1, steps + 1):
        # Ganzzahl-Arithmetik für Geschwindigkeit
        intermediate = [
            int(current[i] + (diffs[i] * step // steps))
            for i in range(4)
        ]
        self.static(intermediate, self.level)
        time.sleep_ms(speed)
"""