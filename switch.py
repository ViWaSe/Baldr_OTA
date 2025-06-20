from machine import Pin, Timer
import sys

class DebouncedButton:
    def __init__(self, pin_num, callback, db_time=200):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
        self.callback = callback
        self.db_time = db_time

        if sys.platform == 'esp32':
            self._timer = Timer(-1)  # -1 for virtual timer instance
        else:
            self._timer = Timer() 

        # set interrupt
        self.pin.irq(handler=self._debounce, trigger=Pin.IRQ_RISING)

    # debounce-timer
    def _debounce(self, pin):
        self._timer.init(mode=Timer.ONE_SHOT, period=self.db_time, callback=self._wrapped_callback)

    # callback to start the actual user function
    def _wrapped_callback(self, timer):
        self.callback()

# Im Hauptprogramm ausführen:

def do_something():
    print("Button pressed!")

button = DebouncedButton(pin_num=14, callback=do_something, db_time=150)