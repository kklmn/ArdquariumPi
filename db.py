# -*- coding: utf-8 -*-
import threading
import os.path as osp
import datetime
import sqlite3 as sql
import supply
import acquire
import logging

DATAFILE = osp.join(osp.dirname(osp.abspath(__file__)), 'data', 'myPi.db')


def get_ios_int():
    pins = (list(supply.outPins.values()) +
            list(supply.inPinsFromRaspberry.values()) +
            list(supply.inPinsFromArduino.values()))

    binStr = ''.join(str(pin['state']) for pin in reversed(pins))
    return int(binStr, 2)
#    res = 0
#    for pin in reversed(pins):
#        res = (res << 1) | pin['state']
#    return res


def get_ios_str(val):
    return "{0:04b}".format(val)


def read_data(timeDeltaDict=None):
    res = []
    con = sql.connect(DATAFILE, detect_types=sql.PARSE_DECLTYPES)
    with con:
        cur = con.cursor()
        exStr = "SELECT * FROM piData"
        if timeDeltaDict is not None:
            pastWhat = list(timeDeltaDict.keys())[0]
            pastCount = list(timeDeltaDict.values())[0]
            exStr += " WHERE time BETWEEN " +\
                "datetime('now', '-{0} {1}') AND 'now'".format(
                    pastCount, pastWhat)
        cur.execute(exStr)
        res = cur.fetchall()
        cur.close()
    con.close()
    return res


class PiBase(object):
    def __init__(self, interval=supply.dbInterval):
        self.interval = interval
        self.allNames = (list(supply.temperatures) +
                         list(supply.sensorsFromArduino) +
                         list(supply.sensorsFromRaspberry))
        self.counter = 0
        self.init_db()
#        self.run()  # or:
        threading.Timer(interval, self.run).start()

    def init_db(self):
        con = sql.connect(DATAFILE, detect_types=sql.PARSE_DECLTYPES)
        with con:
            cur = con.cursor()
            execStr = \
                "CREATE TABLE IF NOT EXISTS piData (time TIMESTAMP, "
            execStr += "ios INTEGER, "
            execStr += ", ".join(tn + " REAL" for tn in self.allNames)
            execStr += ")"
            cur.execute(execStr)
            cur.close()
        con.close()

    def write_data(self):
        ios = get_ios_int()
        lstt = [v['value'] for v in supply.temperatures.values()]
        lstt += [v['value'] for v in supply.sensorsFromArduino.values()]
        lstt += [v['value'] for v in supply.sensorsFromRaspberry.values()]
        con = sql.connect(DATAFILE, detect_types=sql.PARSE_DECLTYPES)
        now = datetime.datetime.now()
        with con:
            cur = con.cursor()
            # use datetime.datetime.now(), not DateTime('now'), for not having
            # to convert the time zones:
            cur.executemany(
                "INSERT INTO piData VALUES (?, ?, {0})".format(
                    ", ".join("?" for t in self.allNames)),
                [[now, ios] + lstt])
            cur.close()
        con.close()
        return now, ios, lstt

    def run(self):
        """Timer() has to be at the end for the case when sensors are not
        readable, i.e. when acquire.get_sensors() does not return. Otherwise,
        if Timer() is at the top, it starts several hanging threads, and each
        of them will send an e-mail."""
        acquire.get_pins()
        acquire.get_sensors(insist=True)
        try:
            now, ios, lstt = self.write_data()
            interval = self.interval
            self.counter += 1
            print(self.counter, now.strftime('%a %d%b%Y %H:%M:%S'), ios, lstt)
        except sql.OperationalError as e:
            logging.error(e)
            print(e)
            interval = 0.5
        threading.Timer(interval, self.run).start()


if __name__ == "__main__":
    PiBase()
#    print(PiBase().read_data())
#    val = get_ios_int()
#    print(val, get_ios_str(val))
