from machine import Pin
import time

class Waterpump():

    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT, value=1)

    def exec(self, duration):
        self.pin.value(0)
        time.sleep(duration)
        self.pin.value(1)


if __name__ == "__main__":
    pump = Waterpump(pin = 21)
    pump.exec(3)
