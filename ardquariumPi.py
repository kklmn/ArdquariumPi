# -*- coding: utf-8 -*-
from .version import __version__, __date__
__author__ = "Konstantin Klementiev"
__email__ = "konstantin DOT klementiev AT gmail DOT com"
__license__ = "MIT license"

import os
from collections import deque
import datetime
from flask import Flask, render_template, request, url_for

import logging
import supply
import acquire
import db
import plots

logging.basicConfig(
    filename='ardquarium.log', format='%(levelname)s:%(message)s',
    level=logging.INFO)

acquire.shouldPostToLocalhost = True
acquire.init_devices()
acquire.init_supply()

if supply.wantCronTable:
    import cron
    try:
        cron.init_cron_tasks(supply.isTest)
    except:  # noqa
        pass

# wantPlot = ''  # none plot
# wantPlot = 'plotly'  # don't use it, this was a try; plotly is very slow
wantPlot = 'mpl'
if wantPlot:
    assert not plots.isTest

app = Flask(__name__)
app.jinja_env.globals.update(zip=zip, enumerate=enumerate)

messagesLen = 33
messages = deque(maxlen=messagesLen)
messageTimes = deque(maxlen=messagesLen)

db.PiBase()


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.normpath(
                os.path.join(app.root_path, endpoint, filename))
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        data = request.get_json(force=True)
        if 'pin' in data:
            try:
                name = data['pin']
                state = data['state']
                how = data['how']
                skipset = 'skipset' in data
            except:  # noqa
                return ""

            stateStr = 'on' if state else 'off'
            message = "{0} {1} {2}".format(how, name, stateStr)
            messages.appendleft(message)
            logging.info(message)
            now = datetime.datetime.now()
            messageTimes.appendleft(now.strftime("%Y/%m/%d, %H:%M:%S"))

            hPins = supply.thermostat['heatingPins'] + \
                supply.thermostat['coolingPins']
            if name in hPins:
                supply.thermostat['lastSwitch'] = now

            if name == 'feeding':
                if state:
                    for nameF in supply.outPins[name]['toSwitchOffBefore']:
                        acquire.set_pin(nameF, 'off')
                else:
                    for nameF in supply.outPins[name]['toSwitchOnAfter']:
                        acquire.set_pin(nameF, 'on')
                supply.feedStartTime = now if state else None

            if not skipset:
                acquire.set_pin(name, stateStr)
        elif 'timedelta' in data:
            td = data['timedelta']
            plots.currentdelta = td
        elif 'yrange' in data:
            plots.yrange = "auto" if plots.yrange != "auto" else "user"
        elif 'thermostat' in data:
            supply.thermostat['active'] = data['state'] == 1
            stateStr = 'on' if supply.thermostat['active'] else 'off'
            name = 'thermostat'
            how = 'Set'
            message = "{0} {1} {2}".format(how, name, stateStr)
            messages.appendleft(message)
            logging.info(message)
            now = datetime.datetime.now()
            messageTimes.appendleft(now.strftime("%Y/%m/%d, %H:%M:%S"))
        return ""  # must return something (not None)

    acquire.get_pins()
    if supply.feedStartTime is None:
        feedCounter = 0
    else:
        now = datetime.datetime.now()
        feedCounter = (supply.outPins['feeding']['delay'] - (
            now - supply.feedStartTime)).seconds

    plotStr = ''
    if wantPlot:
        if 'plotly' in wantPlot:
            dbdata = db.read_data()
            plots.make_plots_plotly(dbdata)
        elif 'mpl' in wantPlot:
            td = plots.timedeltas[plots.currentdelta]
            dbdata = db.read_data(td)
            plotStr, plotHeight = plots.make_plots_mpl(dbdata, td)

    cronTasks = cron.get_cron_tasks() if supply.wantCronTable else {}

    templateData = dict(
        outPins=supply.outPins,
        thermostat=supply.thermostat,
        cronTasks=cronTasks,
        feedCounter=feedCounter,
        temperatures=supply.temperatures,
        temperatureUnit=supply.temperatureUnit,
        temperatureDisplayLimits=supply.temperatureDisplayLimits,
        temperatureColorSectors=supply.temperatureColorSectors,
        sensorsFromArduino=supply.sensorsFromArduino,
        sensorsFromRaspberry=supply.sensorsFromRaspberry,
        wantPlot=wantPlot, plotStr=plotStr, plotHeight=plotHeight,
        timedeltas=plots.timedeltas, currentdelta=plots.currentdelta,
        yrange=plots.yrange,
        messages=messages, messageTimes=messageTimes,
        version=__version__)
    return render_template('aquarium.html', **templateData)


if __name__ == "__main__":
    if supply.isTest:
        print("***************************************")
        print("**  Running in test mode! (no GPIO)  **")
        print("***************************************")
        print()
    logging.info('The app has started')
    app.run(host='0.0.0.0', port=80, debug=False)
