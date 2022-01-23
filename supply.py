# -*- coding: utf-8 -*-
from collections import OrderedDict
import datetime

isTest = True  # for tests without Raspberry Pi's GPIO
# isTest = False  # for the normal run

mplColorLoop = [  # used for plotting temperatures
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
gaugeColor = {"lo": "#038cfc", "ok": "#19cf25", "hi": "#fc3c03"}
gaugeColor['alarm'] = gaugeColor['hi']
gaugeColor['warning'] = "#fcdf03"

outPins = OrderedDict([  # pins of Raspberry Pi as BCM
    # "state" sets initial state, state=None means to get it from GPIO
    ('heater', dict(pin=17, state=0, color='#ff3333')),  # 11
    ('cooler', dict(pin=27, state=0, color='#8888ff')),  # 13
    ('light', dict(pin=22, state=None, color='#ffffff')),  # 15
    ('stream', dict(pin=13, state=0, color='#93acfc')),  # 33
    ('filter-B', dict(pin=6, state=1, color='#55ff55')),  # 31
    ('filter-T', dict(pin=10, state=1, color='#55ff55')),  # 19
    ('filter-S', dict(pin=19, state=1, color='#55ff55')),  # 35
    ('UV-lamp', dict(pin=26, state=1, color='#ddddff')),  # 37
    ('feeding', dict(
        pin=None, state=0, color='#ffff33',
        toSwitchOffBefore=['stream', 'filter-B', 'filter-T', 'filter-S'],
        toSwitchOnAfter=['filter-B', 'filter-T', 'filter-S'],
        delay=datetime.timedelta(seconds=720 if not isTest else 12),
    ))
])

# Temperature sensors. Initial values are for test plots
temperatures = OrderedDict(
    [('T1', dict(value=25, color=mplColorLoop[0])),
     ('T2', dict(value=26, color=mplColorLoop[1])),
     ('T3', dict(value=27, color=mplColorLoop[2])),
     # ('T4', dict(value=28, color=mplColorLoop[3])),
     ])
temperatureUnit = u"ºC"
# 1-wire reading supplier:
temperatureSource = dict(device='arduino')
# temperatureSource = dict(device='raspberry', pin=4)
temperatureDisplayLimits = [25, 31]  # for plots and gauges
temperatureOutlierLimits = [15, 36]  # for plots and thermostat
temperatureAlarmLimits = [24, 29.75]  # for email alarms
temperatureColorSectors = [
    {"lo": 25.0, "hi": 28.2, "color": gaugeColor["lo"]},  # blue, too low
    {"lo": 28.2, "hi": 29.2, "color": gaugeColor["ok"]},  # green, norm
    {"lo": 29.2, "hi": 31.0, "color": gaugeColor["hi"]}]  # red, too high

thermostat = dict(
    active=True,  # None = remove from GUI; False = switch off
    limits=[28.7, 29.2],  # heat if T<lim[0] and cool if T>lim[1]
    delay=datetime.timedelta(minutes=3),  # not sooner after last switch
    heatingPins=['heater'],
    coolingPins=['cooler'],
    color='#bb66bb',
)

# Other sensors. Initial values are for test plots
# Note! These 4 objects:
# sensorsFromRaspberry, inPinsFromRaspberry,
# sensorsFromArduino and inPinsFromArduino
# must exist; they can be empty OrderedDict()

sensorsFromRaspberry = OrderedDict()
#    [('flow', dict(
#        kind=('counter', 5),  # the latter is a GPIO pin as BCM
#        value=15, limits=[5, 50], unit='L/min', color='#ff66ff',
#        colorSectors=[{"lo": 0., "hi": 10, "color": gaugeColor["lo"]},
#                      {"lo": 10, "hi": 20, "color": gaugeColor["ok"]},
#                      {"lo": 20, "hi": 50, "color": gaugeColor["hi"]}])),
#     ('pH', dict(
#        kind=('spi', 0),  # the latter is an ADC channel (MCP3008)
#        value=7, limits=[5, 8], unit='', color='#88ffff',
#        colorSectors=[{"lo": 0, "hi": 6, "color": gaugeColor["lo"]},
#                      {"lo": 6, "hi": 8, "color": gaugeColor["ok"]},
#                      {"lo": 8, "hi": 9, "color": gaugeColor["hi"]}])),
#     ('EC', dict(
#        kind=('spi', 1),  # the latter is an ADC channel (MCP3008)
#        value=500, limits=[200, 700], unit=u'µS/cm', color='#ffff88',
#        colorSectors=[{"lo": 0, "hi": 400, "color": gaugeColor["lo"]},
#                      {"lo": 400, "hi": 1000, "color": gaugeColor["ok"]},
#                      {"lo": 1000, "hi": 10000, "color": gaugeColor["hi"]}])),
#     ])
inPinsFromRaspberry = OrderedDict()
#    [('mains', dict(pin=5, state=1, color='#ffffff')),
#     ('BLE', dict(pin=7, state=1, color='#aaaaaa')),
#     ])

# == if you use Arduino: ======================================================
# it must send a str with space or tab separated values:
# temperatures if temperatureSource['device'] == 'arduino'
# values for all members of sensorsFromArduino
# values for all members of inPinsFromArduino
# =============================================================================
# any of the two limits can be None if you want them automatic.
sensorsFromArduino = OrderedDict(
    [('flow', dict(
        value=400, limits=[0, 800], unit='L/h', color='#ff66ff',
        colorSectors=[{"lo": 0, "hi": 400, "color": gaugeColor["lo"]},
                      {"lo": 400, "hi": 650, "color": gaugeColor["ok"]},
                      {"lo": 650, "hi": 800, "color": gaugeColor["hi"]}])),
     ('pH', dict(
         value=7, limits=[4.5, 7.5], unit='', color='#88ffff',
         colorSectors=[{"lo": 4.5, "hi": 5.25, "color": gaugeColor["alarm"]},
                       {"lo": 5.25, "hi": 6, "color": gaugeColor["warning"]},
                       {"lo": 6, "hi": 7.5, "color": gaugeColor["ok"]}])),
     ('EC', dict(
         value=350, limits=[0, 700], unit=u'µS/cm', color='#ffff88',
         colorSectors=[{"lo": 0, "hi": 100, "color": gaugeColor["lo"]},
                       {"lo": 100, "hi": 400, "color": gaugeColor["ok"]},
                       {"lo": 400, "hi": 700, "color": gaugeColor["hi"]}])),
     ('DO', dict(
         value=6, limits=[0, 8], unit=u'mg/L', color='#88ff88',
         colorSectors=[{"lo": 0, "hi": 2, "color": gaugeColor["alarm"]},
                       {"lo": 2, "hi": 5, "color": gaugeColor["warning"]},
                       {"lo": 5, "hi": 8, "color": gaugeColor["ok"]}])),
     ])
inPinsFromArduino = OrderedDict(
    [('mains', dict(state=1, color='#ffffff')),
     ('BLE', dict(state=0, color='#77ff77')),
     ('leak', dict(state=0, color='#99bbff')),
     ])

# USB port where Arduino is connected, check it with "ls /dev/tty*"
# portArduino = '/dev/ttyUSB*'  # this works with Uno|Nano
portArduino = '/dev/ttyACM*'  # this works with Nano Every
portArduinoBaudRate = 115200  # must match the value in ardquarium.ino
arduinoReadAttempts = 120
arduinoReadDelay = 1.  # s. When waiting for arduino serial
arduinoBootDelay = 12.  # s. When rebooting arduino after exceptions

plotPins = ['heater', 'cooler', 'mains', 'BLE']  # plot state of these pins
gaugePins = ['mains', 'BLE', 'leak']  # display state of these pins by gauges

wantEmailAlarms = ['arduino', 'temperature', 'mains', 'BLE',  'leak',
                   'intrusion']
if wantEmailAlarms:
    delayUntilArduinoAlarm = datetime.timedelta(minutes=10)
    delayUntilTemperatureAlarm = datetime.timedelta(minutes=10)
    delayUntilMainsAlarm = datetime.timedelta(minutes=10)
    delayUntilBLEAlarm = datetime.timedelta(hours=2)
    delayUntilLeakAlarm = datetime.timedelta(minutes=0)
    intervalBetweenEmails = datetime.timedelta(minutes=15)

wantCronTable = True  # show switch time from crontable for each pin in outPins

dbInterval = 10. if not isTest else 2.  # database write interval in sec
