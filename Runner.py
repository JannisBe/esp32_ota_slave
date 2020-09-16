from network import WLAN
import machine
import time
import utime
import logging

from settings import *
from .package_settings import *

from src.OTAUpdater.OTAUpdater import OTAUpdater
from src.OTAUpdater.HttpUtility import connected_to_network
from .Waterpump import Waterpump
from .SoilMoisture import SoilMoisture
from .MQTT.mqtt import MQTTClient, MQTTException

waterpumps = []

def diff_in_minutes(t):
    """
        Returns difference in minutes between time and now
    """
    if t is False:
        return "-"
    now = utime.time()
    then = utime.mktime((t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]))
    diff = now - then
    return int(diff / 60)

def waterpump_callback(topic, msg):
    global waterpumps
    n = int(topic[len(WATERPUMPCHANNEL):])
    waterpumps[n]['obj'].exec(int(msg))
    waterpumps[n]['last_value'] = int(msg)
    waterpumps[n]['last_activated'] = utime.localtime(utime.time())
    return

def get_latest_waterpump_activation():
    global waterpumps
    last = 0
    lasti = 0
    lastval = 0
    for i, w in enumerate(waterpumps):
        t = w['last_activated']
        tstamp = utime.mktime((t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]))
        if tstamp > last:
            last = tstamp
            lastt = t
            lasti = i
            lastval = w['last_value']
    return lastt, lasti, lastval

def run():
    """
        Main Routine to execute
    """

    logging.info('------------')
    logging.info('starting setup')
    logging.info('------------')

    #SET INITIAL TIME
    rtc = machine.RTC()
    rtc.datetime((2020,1,1,0,0,0,0,0))

    def settimeout(duration):
        pass
    try:
        client = MQTTClient(BROKER_CLIENT, BROKER_URL, 1883)
        client.settimeout = settimeout
        client.connect()
    except MQTTException:
        logging.info('SERVER NOT RESPONDING')
        logging.info('RESET')
        time.sleep(5)
        machine.reset()
    except Exception as e:
        logging.info(e)


    #Initialize Waterpumps
    global waterpumps
    for pin in WATERPUMPPINS:
        waterpumps.append({
            'obj': Waterpump(pin),
            'last_activated': utime.localtime(utime.time()),
            'last_value': 0
        })

    soilmoisturesensors = []
    for pin in SOILMOISTUREPINS:
        soilmoisturesensors.append({
            'obj': SoilMoisture(pin),
            'last_checked': False,
            'last_value': False
        })

    logging.info('------------')
    logging.info('starting loop')
    logging.info('------------')
    time.sleep(1)

    #Waterpump
    client.set_callback(waterpump_callback)
    for i, pump in enumerate(waterpumps):
        client.subscribe(topic=WATERPUMPCHANNEL + str(i), qos=2)

    # Loop
    while True:
        while not connected_to_network(timeout=20, restart=True):
            time.sleep(1)
        #SoilMoisture
        for i, sensor in enumerate(soilmoisturesensors):
            channel = SOILMOISTURECHANNEL + str(i)
            val = sensor['obj'].exec()
            try:
                sensor['last_value'] = int(val)
                sensor['last_checked'] = utime.localtime(utime.time())
            except:
                pass
            client.publish(channel, str(val))
            logging.info('s{0} {1}m ago: {2}'.format(
                str(i),
                str(diff_in_minutes(sensor['last_checked'])),
                str(sensor['last_value'])
            ))

        pump, pumpi, pumpval = get_latest_waterpump_activation()
        logging.info('w{0} {1}m ago: {2}'.format(
            str(pumpi),
            str(diff_in_minutes(pump)),
            str(pumpval)
        ))
        client.check_msg()
        machine.deepsleep(15000) # 20sec
