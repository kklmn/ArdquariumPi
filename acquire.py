# -*- coding: utf-8 -*-
import glob
import time
import datetime
import subprocess
import numpy as np
import requests
import supply
import logging
import os, sys
if sys.platform.lower() == "win32":
    os.system('color')

if not supply.isTest:
    try:
        import RPi.GPIO as GPIO
    except ImportError as e:
        raise type(e)(
            str(e) +
            "\ntry to test without GPIO by setting supply.isTest = True")

shouldPostToLocalhost = False  # the host server will set True when it starts


class PrintStyle():
    BLACK = lambda x: '\033[30m' + str(x)
    RED = lambda x: '\033[31m' + str(x)
    GREEN = lambda x: '\033[32m' + str(x)
    YELLOW = lambda x: '\033[33m' + str(x)
    BLUE = lambda x: '\033[34m' + str(x)
    MAGENTA = lambda x: '\033[35m' + str(x)
    CYAN = lambda x: '\033[36m' + str(x)
    WHITE = lambda x: '\033[37m' + str(x)
    UNDERLINE = lambda x: '\033[4m' + str(x)
    RESET = lambda x: '\033[0m' + str(x)


def init_devices():
    if supply.isTest:
        for name in supply.outPins:
            pin = supply.outPins[name]['pin']
            if pin is not None:
                state = supply.outPins[name]['state']
                if state is None:
                    supply.outPins[name]['state'] = 0
        return

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for name in supply.outPins:
        pin = supply.outPins[name]['pin']
        if pin is not None:
            GPIO.setup(pin, GPIO.OUT)
            state = supply.outPins[name]['state']
            if state is None:
                state = int(GPIO.input(pin) != GPIO.HIGH)
                supply.outPins[name]['state'] = state
            set_pin(name, state)

    if supply.temperatureSource['device'].startswith('rasp'):  # raspberry Pi
        # if you prefer a physical pul-up, remove it here:
        GPIO.setup(supply.temperatureSource['pin'], GPIO.IN,
                   # pull_up_down=GPIO.PUD_UP
                   )
        w1Dir = '/sys/bus/w1/devices/'
        deviceFolders = glob.glob(w1Dir + '28*')
        supply.deviceFiles = [df + '/w1_slave' for df in deviceFolders]
        assert len(deviceFolders) == len(supply.temperatures)

    for name in supply.inPinsFromRaspberry:
        pin = supply.inPinsFromRaspberry[name]['pin']
        GPIO.setup(pin, GPIO.IN)

    if True:
        supply.lenTemperaturesArd = len(supply.temperatures) \
            if supply.temperatureSource['device'].startswith('ardu') else 0
        supply.lenSensorsArd = len(supply.sensorsFromArduino)
        supply.lenInPinsArd = len(supply.inPinsFromArduino)
    else:  # to test with GPIO but without Arduino:
        supply.lenTemperaturesArd = 0
        supply.lenSensorsArd = 0
        supply.lenInPinsArd = 0
        supply.deviceFiles = []
    if (supply.lenTemperaturesArd + supply.lenSensorsArd +
            supply.lenInPinsArd > 0):
        import serial
        supply.serial = serial
        arduinoFolder = glob.glob(supply.portArduino)[0]
        try:
            supply.arduinoSerial = serial.Serial(
                arduinoFolder, supply.portArduinoBaudRate,
                timeout=supply.arduinoBootDelay)
            supply.arduinoSerial.reset_input_buffer()
            supply.lastArduinoRes = []
            supply.lastArduinoTime = datetime.datetime.now()
        except serial.serialutil.SerialException as e:
            if supply.wantEmailAlarms:
                supply.arduino_alarm("Arduino is not connected!")
                raise e
            else:
                raise IOError("Cannot read from Arduino!")

    spiSensorsFromRaspberry = [
        sensor['kind'][1] for sensor in supply.sensorsFromRaspberry.values()
        if sensor['kind'][0].startswith('spi')]
    if len(spiSensorsFromRaspberry) > 0:
        import spidev
        supply.spi = spidev.SpiDev()
        supply.spi.open(0, 0)

    counterSensorsFromRaspberry = [
        sensor['kind'][1] for sensor in supply.sensorsFromRaspberry.values()
        if sensor['kind'][0].startswith('cou')]
    if len(counterSensorsFromRaspberry) > 0:
        pulseCounter = \
            {c: [0, 0, time.time()] for c in counterSensorsFromRaspberry}

        def _count(channel):
            pulseCounter[channel][0] += 1

        for sensor in counterSensorsFromRaspberry:
            GPIO.setup(sensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(sensor, GPIO.FALLING, callback=_count)


def init_supply():
    for dd in list(supply.outPins.values()) + [supply.thermostat]:
        color = dd['color'][1:]  # without the leading '#'
        cr, cg, cb = [int(int(color[i:i+2], 16) * 0.75)
                      for i in range(0, len(color), 2)]
        dd['dimmedColor'] = '#' + ''.join(hex(c)[2:] for c in (cr, cg, cb))
    now = datetime.datetime.now()
    supply.thermostat['lastSwitch'] = now - supply.thermostat['delay']
    supply.lastGoodArduinoTime = now
    supply.lastGoodTemperatureTime = now
    supply.lastGoodMainsTime = now
    supply.lastGoodBLETime = now
    supply.lastEmailSentTime = now
    supply.aveT = None
    supply.feedStartTime = None

    if supply.wantEmailAlarms:
        import alarm
        assert alarm.check_set()
        supply.arduino_alarm = alarm.send_email
    else:
        supply.arduino_alarm = None


def set_pin(name, state):
    if state == 'switch':
        supply.outPins[name]['state'] ^= 1
    else:
        supply.outPins[name]['state'] = 1 if state in ('on', 'yes', 1) else 0

    pin = supply.outPins[name]['pin']
    if pin is None or supply.isTest:
        return
    # GPIO.HIGH means "off" for relays
    GPIO.output(pin, GPIO.LOW if supply.outPins[name]['state'] else GPIO.HIGH)


def get_pins():
    if supply.isTest:
        return

    for name in supply.outPins:
        pin = supply.outPins[name]['pin']
        if pin is None:
            continue
        state = int(GPIO.input(pin) == GPIO.HIGH)
        supply.outPins[name]['state'] = int(not state)
    for name in supply.inPinsFromRaspberry:
        pin = supply.inPinsFromRaspberry[name]['pin']
        state = int(GPIO.input(pin) == GPIO.HIGH)
        supply.outPins[name]['state'] = int(state)

    if supply.feedStartTime is not None:
        now = datetime.datetime.now()
        if now - supply.feedStartTime > supply.outPins['feeding']['delay']:
            for nameF in supply.outPins['feeding']['toSwitchOnAfter']:
                set_pin(nameF, 'on')
            set_pin('feeding', 'off')
            supply.feedStartTime = None
            dictToSend = {"pin": 'feeding', "state": 0,
                          "how": "Timer-switched", "skipset": 1}
            if shouldPostToLocalhost:
                try:
                    requests.post('http://localhost:80', json=dictToSend)
                except:  # noqa
                    pass
            try:
                requests.get('http://localhost:80')
            except:  # noqa
                pass


def _get_one_temperature_raspberry(fname):
    catdata = subprocess.Popen(
        ['cat', fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, _ = catdata.communicate()
    lines = out.decode('utf-8').split('\n')
    if lines[0].strip()[-3:] != 'YES':
        time.sleep(0.5)
        _get_one_temperature_raspberry(fname)
    equals_pos = lines[1].find('t=')
    if equals_pos == -1:
        return
    temp_string = lines[1][equals_pos+2:]
    res = float(temp_string) / 1000.0  # in C
    if "F" in supply.temperatureUnit:
        res = res*1.8 + 32
    return res


def _email_body():
    try:
        return "Cannot read from Arduino!\n" + \
            "Last succsessful reading on {0[0]} at {0[1]}:\n"\
            .format(str(supply.lastArduinoTime).split('.')[0].split(' ')) +\
            ", ".join([str(r) for r in supply.lastArduinoRes])
    except AttributeError:
        return


def _read_from_arduino(insist=True, attempt=0):
    now = datetime.datetime.now()
    lenExpected = supply.lenTemperaturesArd + supply.lenSensorsArd + \
        supply.lenInPinsArd
    try:
        ra = 0
        while supply.arduinoSerial.in_waiting <= 0:
            ra += 1
            time.sleep(supply.arduinoReadDelay)
            if ra >= supply.arduinoReadAttempts:
                raise ValueError('Arduino not ready')
        buf = supply.arduinoSerial.readline()
        try:
            res = [float(v) for v in buf.split()]
        except ValueError:
            bufOut = buf[:-2].decode()  # trailing \r\n
            try:
                if "temperature device" in bufOut:
                    bufS = bufOut.split()
                    PColor = PrintStyle.RED if int(bufS[1]) < \
                        supply.lenTemperaturesArd else PrintStyle.GREEN
                    print(PrintStyle.RESET(bufOut[:5]), PColor(bufOut[5:8]),
                          PrintStyle.RESET(bufOut[8:]))
                else:
                    raise Exception
            except Exception:
                print(bufOut)
            return _read_from_arduino(attempt=attempt)
        if len(res) != lenExpected:
            out = 'Wrong length={0} of arduino response, expected length={1}'\
                  '\ngot: {2}'.format(len(res), lenExpected, res)
            print(out)
            logging.warning(out)
            raise ValueError(out)
        supply.arduinoSerial.reset_input_buffer()
        supply.arduinoSerial.write("alive".encode())
        supply.lastGoodArduinoTime = now
        return res
    except (supply.serial.serialutil.SerialException, ValueError,
            OSError) as e:
        if not insist:
            return []
        try:
            supply.arduinoSerial.close()
            arduinoFolder = glob.glob(supply.portArduino)[0]
            print('Arduino rebooting attempt #{0}'.format(attempt+1))
            supply.arduinoSerial = supply.serial.Serial(
                arduinoFolder, supply.portArduinoBaudRate,
                timeout=supply.arduinoBootDelay)
            time.sleep(supply.arduinoBootDelay)
        except Exception as e:  # noqa
            logging.warning(e)
        if attempt >= supply.arduinoReadAttempts:
            if supply.wantEmailAlarms:
                if ((now - supply.lastGoodArduinoTime) >
                        supply.delayUntilArduinoAlarm):
                    supply.arduino_alarm(_email_body())
                    supply.lastEmailSentTime = now
                    return []
            else:
                out = "Cannot read from Arduino!"
                logging.error(out)
                raise IOError(out)
        return _read_from_arduino(attempt=attempt+1)


def _get_spi_raspberry(adcnum):
    supply.spi.max_speed_hz = 1350000
    raw = supply.spi.xfer2([1, (8+adcnum) << 4, 0])
    data = ((raw[1] & 3) << 8) + raw[2]
    return data


def get_sensors(insist=True):
    if supply.isTest:
        allSensors = (list(supply.temperatures.values()) +
                      list(supply.sensorsFromArduino.values()) +
                      list(supply.sensorsFromRaspberry.values()))
        rr = 0.1 * (np.random.random(len(allSensors)) - 0.5)
        for v, r in zip(allSensors, rr):
            v['value'] = round(v['value'] + r, 3)
    else:
        if (supply.lenTemperaturesArd + supply.lenSensorsArd +
                supply.lenInPinsArd > 0):
            arduinoRes = _read_from_arduino(insist)
            if arduinoRes:
                supply.lastArduinoRes = arduinoRes
                supply.lastArduinoTime = datetime.datetime.now()
        else:
            arduinoRes = []

        if supply.lenTemperaturesArd > 0:  # temperatures from arduino
            for v, ta in zip(supply.temperatures.values(), arduinoRes):
                v['value'] = ta
        else:  # temperatures from raspberry
            for v, df in zip(supply.temperatures.values(), supply.deviceFiles):
                v['value'] = _get_one_temperature_raspberry(df)

        for v, sa in zip(supply.sensorsFromArduino.values(),
                         arduinoRes[supply.lenTemperaturesArd:]):
            v['value'] = sa

        for v, pa in zip(supply.inPinsFromArduino.values(), arduinoRes[
                supply.lenTemperaturesArd+supply.lenSensorsArd:]):
            v['state'] = int(pa)

        for key, sensor in supply.sensorsFromRaspberry.items():
            channel = sensor['kind'][1]
            if sensor['kind'][0].startswith('cou'):
                now = time.time()
                ct = pulseCounter[channel][0]
                ct0 = pulseCounter[channel][1]
                then = pulseCounter[channel][2]
                rate = (ct - ct0) / (now - then)
                pulseCounter[channel][1] = ct
                pulseCounter[channel][2] = now
                if key == 'flow':
                    sensor['value'] = rate / 5.5 * 60  # L/h
            if sensor['kind'][0].startswith('spi'):
                channel = sensor['kind'][1]
                volt = _get_spi_raspberry(channel) * 5.0 / 1023.
                if key == 'turbidity':
                    sensor['value'] = -1120.4*volt**2 + 5742.3*volt - 4352.9
                if key == 'pH':
                    offset_pH = 7.0 - 6.88  # as measured
                    sensor['value'] = 3.5*volt + offset_pH
                if key == 'EC':
                    sensor['value'] = 1000 * volt / 820.0 / 200.0

    if supply.thermostat['active']:
        thermostat()

    check_alarms()


def _set_thermostat_pin(name, cond, now):
    state = int(cond)
    if supply.outPins[name]['state'] == state:  # do nothing
        return
    set_pin(name, state)
    supply.thermostat['lastSwitch'] = now
    dictToSend = {"pin": name, "state": state, "how": "Auto-switched",
                  "skipset": 1}
    if shouldPostToLocalhost:
        try:
            requests.post('http://localhost:80', json=dictToSend)
        except:  # noqa
            pass


def thermostat():
    now = datetime.datetime.now()
    if (now - supply.thermostat['lastSwitch']) < supply.thermostat['delay']:
        return
    allT = [v['value'] for v in supply.temperatures.values() if
            supply.temperatureOutlierLimits[0] < v['value'] <
            supply.temperatureOutlierLimits[1]]
    if len(allT) == 0:
        supply.aveT = None
        return
    supply.aveT = sum(allT) / len(allT)

    for tpn in supply.thermostat['heatingPins']:
        _set_thermostat_pin(
            tpn, supply.aveT < supply.thermostat['limits'][0], now)
    for tpn in supply.thermostat['coolingPins']:
        _set_thermostat_pin(
            tpn, supply.aveT > supply.thermostat['limits'][1], now)


def check_alarms():
    if not supply.wantEmailAlarms:
        return
    now = datetime.datetime.now()
    alarmTxt = ""

    if 'mains' in supply.wantEmailAlarms:
        if 'mains' in supply.inPinsFromRaspberry:
            mainsDict = supply.inPinsFromRaspberry['mains']
        elif 'mains' in supply.inPinsFromArduino:
            mainsDict = supply.inPinsFromArduino['mains']
        else:
            mainsDict = None
        if mainsDict is not None:
            if mainsDict['state'] == 0:
                if ((now - supply.lastGoodMainsTime) >
                        supply.delayUntilMainsAlarm):
                    alarmTxt += "The power supply is off!\n"
            else:
                supply.lastGoodMainsTime = now

    if 'BLE' in supply.wantEmailAlarms:
        if 'BLE' in supply.inPinsFromRaspberry:
            bleDict = supply.inPinsFromRaspberry['BLE']
        elif 'BLE' in supply.inPinsFromArduino:
            bleDict = supply.inPinsFromArduino['BLE']
        else:
            bleDict = None
        if bleDict is not None:
            if bleDict['state'] == 0:
                if ((now - supply.lastGoodBLETime) >
                        supply.delayUntilBLEAlarm):
                    alarmTxt += "BLE is not connected!\n"
            else:
                supply.lastGoodBLETime = now

    if 'temperature' in supply.wantEmailAlarms:
        if supply.aveT is None:
            if ((now - supply.lastGoodTemperatureTime) >
                    supply.delayUntilTemperatureAlarm):
                alarmTxt += u"All temperature readings are bad!"
        else:
            if (supply.temperatureAlarmLimits[0] < supply.aveT <
                    supply.temperatureAlarmLimits[1]):
                supply.lastGoodTemperatureTime = now
            else:
                if ((now - supply.lastGoodTemperatureTime) >
                        supply.delayUntilTemperatureAlarm):
                    alarmTxt += u"Dangerous temperature {0:.3f}{1}!".format(
                        supply.aveT, supply.temperatureUnit)

    if alarmTxt and (
            (now - supply.lastEmailSentTime) > supply.intervalBetweenEmails):
        try:
            supply.arduino_alarm(alarmTxt)
            supply.lastEmailSentTime = now
        except Exception as e:
            logging.error(e)


if __name__ == "__main__":
    time.sleep(1)
    get_pins()
    get_sensors()
    print('pins = {0}'.format([v['state'] for v in supply.outPins.values()]))
    print('temperatures = {0}'.format(
        [v['value'] for v in supply.temperatures.values()]))
    for key, sensor in supply.sensorsFromRaspberry.items():
        print('{0} = {1:.3f} {2}'.format(key, sensor['value'], sensor['unit']))
    for key, sensor in supply.sensorsFromArduino.items():
        print('{0} = {1:.3f} {2}'.format(key, sensor['value'], sensor['unit']))
