import argparse
import requests
import supply
import logging

shouldPostToLocalhost = True

logging.basicConfig(
    filename='crontab-GPIO.log', format='%(levelname)s:%(message)s',
    level=logging.INFO)

if not supply.isTest:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for name in supply.outPins:
        pin = supply.outPins[name]['pin']
        if pin is None:
            continue
        if not (2 <= pin <= 27):
            continue
        GPIO.setup(pin, GPIO.OUT)


def set_pin(name, state):
    if state == 'switch':
        supply.outPins[name]['state'] ^= 1
    else:
        supply.outPins[name]['state'] = 1 if state in ('on', 'yes', 1) else 0

    pin = supply.outPins[name]['pin']
    if pin is None or supply.isTest:
        return
    GPIO.output(pin, GPIO.LOW if supply.outPins[name]['state'] else GPIO.HIGH)
    logging.info("GPIO pin {0} set {1} by crontab".format(
        name, 'on' if state in ('on', 'yes', 1) else 'off'))
    dictToSend = {"pin": name, "state": 1 if state in ('on', 'yes', 1) else 0,
                  "how": "Crontab-switched", "skipset": 1}
    if shouldPostToLocalhost:
        try:
            requests.post('http://localhost:80', json=dictToSend)
        except:  # noqa
            pass


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Switches GPIO pins on and off.')

    parser.add_argument(
        '--name', action='append', nargs=2, metavar=('name', 'state'),
        help="a pair of pin name and state, e.g. "
        "'light on', 'light off' or 'light switch'")

    args = parser.parse_args()
    # args = parser.parse_args("--name light on --name stream off".split())
    # print(args.name)
    # >> [['light', 'on'], ['stream', 'off']]

    get_pins()

    for name, pinState in args.name:
        if pinState not in ['on', 'off', 'switch']:
            raise ValueError("unknown state")
        if name in supply.outPins:
            set_pin(name, pinState)
            pin = supply.outPins[name]['pin']
            print("set {0} (pin # {1}) {2}".format(name, pin, pinState))
        else:
            raise ValueError("unknown pin")
