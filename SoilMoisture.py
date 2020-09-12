from machine import Pin, ADC
import time

class SoilMoisture():

    def __init__(self, pin):
        self.pin = Pin(pin)
        self.adc = ADC(self.pin)
        self.adc.atten(self.adc.ATTN_11DB)

    def test(self, times=60):
        for i in range(times):
            print(self.adc.read())
            time.sleep(1)

    def exec(self):
        return self.adc.read()
