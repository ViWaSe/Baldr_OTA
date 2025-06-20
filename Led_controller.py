version = "0.1.0"

from machine import Pin

class LedInterface:
    def on(self): pass
    def off(self): pass
    def toggle(self): pass
    def is_on(self): return False

class LedDummy(LedInterface):
    def __init__(self) -> None:
        self.state = False

    def on(self): self.state = True
    def off(self): self.state = False
    def toggle(self): self.state = not self.state
    def is_on(self): return self.state

class StandardLed(LedInterface):
    def __init__(self, pin: Pin) -> None:
        self.led = pin

    def on(self): self.led.on()
    def off(self): self.led.off()
    def toggle(self): self.led.value(not self.led.value())
    def is_on(self): return self.led.value() == 1

class InvertedLed(LedInterface):
    def __init__(self, pin: Pin) -> None:
        self.led = pin

    def on(self): self.led.off()
    def off(self): self.led.on()
    def toggle(self): self.led.value(not self.led.value())
    def is_on(self): return self.led.value() == 0

class LedController:
    def __init__(self, is_pico: bool, settings: dict, led_active: bool = True):
        self.led_active = led_active

        if not self.led_active:
            self.led = LedDummy()
            return

        if is_pico:
            pin = Pin('LED', Pin.OUT, value=0)
            self.led = StandardLed(pin)
        else:
            onboard_led_pin = settings.get('onboard_led')
            led_inverted    = settings.get('led_inverted', False)
            pin = Pin(onboard_led_pin, Pin.OUT)
            self.led = InvertedLed(pin) if led_inverted else StandardLed(pin)

    def on(self):
        if self.led_active:
            self.led.on()

    def off(self):
        if self.led_active:
            self.led.off()

    def toggle(self):
        if self.led_active:
            self.led.toggle()

    def is_on(self):
        return self.led.is_on() if self.led_active else False

    def set_active(self, active: bool):
        self.led_active = active
        if not active:
            self.led.off()

# Example of usage:
# settings = {"onboard_led": 2, "led_inverted": True}
# onboard_led = LedController(is_pico=False, settings=settings)
