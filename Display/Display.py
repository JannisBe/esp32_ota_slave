from machine import Pin, I2C
from . import SSD1306
import time
import machine
import logging

###############
### LOGGING ###
###############
logging.basicConfig(filename='main.log',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            level=logging.DEBUG)


class Display:
    _instance = None

    def __init__(self, width = 128, height = 64, scl_pin = 15, sda_pin = 4, physical_available=False):
        # ESP32 Pin assignment
        self.physical_available = physical_available
        if physical_available:
            rst = Pin(16, Pin.OUT)
            rst.value(1)
            self.oled_width = width
            self.oled_height = height
            self.current_x = 0
            self.max_lines = int(self.oled_height / 10)
            self.scl = Pin(scl_pin, Pin.OUT, Pin.PULL_UP)
            self.sda = Pin(sda_pin, Pin.OUT, Pin.PULL_UP)
            self.i2c = I2C(scl=self.scl, sda=self.sda, freq=450000)
            self.oled = SSD1306.SSD1306_I2C(self.oled_width, self.oled_height, self.i2c, addr=0x3c)
            self.max_letters = int(self.oled_width / 8)

    def reset(self):
        if self.physical_available:
            self.current_x = 0
            self.oled.init_display()

    def next_line(self):
        if self.physical_available:
            self.current_x += 10
            if self.current_x > self.oled_height:
                self.current_x = 0
                self.reset()

    def log(self, message, overwrite=False, debug=False, nodisplay=False):
        if self.physical_available:
            if len(message) <= self.max_letters:
                if debug:
                    logging.info('{0}'.format(message))
                    print(message)
                if not nodisplay:
                    self.oled.text(message, 0, self.current_x)
            else:
                if debug:
                    logging.info('{0}'.format(message))
                print(message)
                chunks = [message[i:i+self.max_letters] for i in range(0, len(message), self.max_letters)]
                for chunk in chunks:
                    self.log(chunk, debug=False)
                # TODO: add auto chunking
                # chunks, chunk_size = len(str), len(str) // self.max_letters
                # print("chunks: {0}, chunk_size: {1}, max_letters: {2}".format(chunks, chunk_size, self.max_letters))
                # for i in range(chunks):
                #     print(str[i:i+chunk_size])
                #     self.log(str[i:i+chunk_size])
            if not overwrite:
                self.next_line()
            self.oled.show()
        else:
            print(message)

    def signalize(self, message=None, n = 10):
        if self.physical_available:
            if message:
                self.log(message)
            for i in range(n):
                self.oled.invert(True)
                time.sleep(0.1)
                self.oled.invert(False)
                time.sleep(0.1)

    def error(self):
        if self.physical_available:
            self.reset()
            self.log('UNDEFINED ERROR')
            self.log('RESET')
            self.signalize(n=5)
            time.sleep(5)
        machine.reset()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Display, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

display = Display()
