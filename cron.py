# -*- coding: utf-8 -*-
import subprocess
from datetime import datetime
from croniter import croniter

cronTable = None

cronTest = \
"""
20 7 * * 1-5 /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name light on
45 8 * * 1-5 /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name light off
30 9 * * 6,7 /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name light on
30 17 * * 1-5 /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name light on
0 23 * * * /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name light off

0 11 * * * /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name filter-S on
0 20 * * * /usr/bin/python3 /home/pi/ArdquariumPi/gpioswitch.py --name filter-S off
"""


def init_cron_tasks(isTest=False):
    global cronTable
    txt = cronTest if isTest else subprocess.Popen(
        # ['crontab', '-l'],
        ['crontab', '-l', '-u', 'pi'],
        stdout=subprocess.PIPE,
        encoding='utf8').communicate()[0]
    cronTable = [l.strip().split(' ') for l in txt.split("\n")
                 if l and not l.startswith('#') and "gpioswitch" in l]
    if cronTable:
        cronTable = [[' '.join(l[:5]), l[-2], l[-1]] for l in cronTable]
    return cronTable


def get_cron_tasks():
    res = {}
    if not cronTable:
        return res
    now = datetime.now()
    for cron, what, state in cronTable:
        # print(cron, what, state)
        cli = croniter(cron, now)
        prevt, nextt = cli.get_prev(datetime), cli.get_next(datetime)
        if what in res:
            if 'prev'+state in res[what]:
                condPrev = prevt >= res[what]['prev'+state]
                condNext = nextt <= res[what]['next'+state]
            else:
                condPrev, condNext = True, True
        else:
            res[what] = {}
            condPrev, condNext = True, True
        if condPrev:
            res[what]['prev'+state] = prevt
        if condNext:
            res[what]['next'+state] = nextt

    bad = []
    for what in res:
        try:
            if res[what]['prevon'] > res[what]['prevoff']:  # now on
                res[what]['str'] = 'on by crontab\n{0} – {1}'.format(
                    res[what]['prevon'].strftime('%H:%M'),
                    res[what]['nextoff'].strftime('%H:%M'))
            else:  # now off
                res[what]['str'] = 'off by crontab\n{0} – {1}'.format(
                    res[what]['prevoff'].strftime('%H:%M'),
                    res[what]['nexton'].strftime('%H:%M'))
        except KeyError:
            bad.append(what)

    for what in bad:
        del res[what]

    return res
