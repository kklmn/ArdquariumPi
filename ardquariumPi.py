# -*- coding: utf-8 -*-
__author__ = "Konstantin Klementiev"
__email__ = "konstantin DOT klementiev AT gmail DOT com"
__license__ = "MIT license"
from __version import __version__
print('ArdquariumPi {0}'.format(__version__))

import os
from collections import deque
import datetime
from flask import (Flask, render_template, request, url_for, Response, abort,
                   redirect)
import logging
import requests
import supply
import acquire
import db
import plots
import camera
import __secret

viewstates = dict(  # the bittons in the upper left corner
    plots=[True, True],  # [selected, button enabled]
    messages=[True, True],  # [selected, button enabled]
    camera=[False, camera.enabled],  # [unselected, en(dis)abled]
    )

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

# allowRemote = True
allowRemote = False  # outside of trustedAddresses
trustedProxies = ()
trustedAddresses = ('192.168', '127.0.0')  # checked by startswith()
userAttempts = {}  # {address: no_of_attempts}
userAttemptsMax = 3

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


def get_remote():
    remote = str(request.remote_addr)
    if trustedProxies:
        route = list(request.access_route)
        while remote in trustedProxies:
            remote = route.pop()
    return remote


def is_known():
    remote = get_remote()

    for trustedAddress in trustedAddresses:
        if remote.startswith(trustedAddress):
            return True

    if not allowRemote:
        return False

    jdata = request.get_json(force=True, silent=True)
    try:
        if jdata["key"] == __secret.iftttKey:
            return True
    except Exception:
        pass

    if remote in userAttempts:
        if userAttempts[remote] == 0:
            return True

    return False  # address is unknown


@app.route('/login', methods=['GET', 'POST'])
def login():
    remote = get_remote()
    if remote in userAttempts:
        if userAttempts[remote] > userAttemptsMax:
            return abort(403)  # forbidden

    if request.method == 'POST':
        if request.form['username'] != __secret.pageUser or \
                request.form['password'] != __secret.pagePassword:
            if remote in userAttempts:
                userAttempts[remote] += 1
            else:
                userAttempts[remote] = 1
            if userAttempts[remote] > userAttemptsMax:
                lenIntr = len(userAttempts)
                msg = "{0} detected intruder{1}".format(
                    lenIntr, 's' if lenIntr > 1 else '')
                logging.info(msg)
                print(msg)
                if 'intrusion' in supply.wantEmailAlarms:
                    alarmTxt = u"Intrusion attempts from {0}".format(remote)
                    try:
                        supply.arduino_alarm(alarmTxt)
                        alarmMsg = "Intrusion attempt {0}".format(remote)
                        dictToSend = {"info": alarmMsg}
                        requests.post('http://localhost:80', json=dictToSend)
                    except Exception as e:
                        print(e)
                        logging.error(e)

            return abort(403)  # forbidden
        else:  # successful login
            userAttempts[remote] = 0
            if 'intrusion' in supply.wantEmailAlarms:
                alarmTxt = u"Remote connection from {0}".format(remote)
                logging.info(alarmTxt)
                print(alarmTxt)
                try:
                    supply.arduino_alarm(alarmTxt)
                    alarmMsg = "Remote {0}".format(remote)
                    dictToSend = {"info": alarmMsg}
                    requests.post('http://localhost:80', json=dictToSend)
                except Exception as e:
                    print(e)
                    logging.error(e)
            return redirect(url_for('main'))

    msg = "{0} wants to log in".format(remote)
    logging.info(msg)
    print(msg)
    return render_template('login.html')


@app.route("/", methods=["GET", "POST"])
def main():
    if not is_known():
        if allowRemote:
            return redirect(url_for('login'))
        else:
            return abort(403)  # forbidden

    if request.method == "POST":
        data = request.get_json(force=True)
        if 'viewpanel' in data:
            td = data['viewpanel']
            viewstates[td][0] = not viewstates[td][0]
        elif 'pin' in data:
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
        elif 'plotdelta' in data:
            td = data['plotdelta']
            plots.currentDelta = td
        elif 'yrange' in data:
            plots.yrange = "auto" if plots.yrange != "auto" else "user"
        elif 'cameradelta' in data:
            td = data['cameradelta']
            camera.currentDelta = td
        elif 'info' in data:
            message = data['info']
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
    plotHeight = 360
    if wantPlot and viewstates['plots'][0]:
        if 'plotly' in wantPlot:
            dbdata = db.read_data()
            plots.make_plots_plotly(dbdata)
        elif 'mpl' in wantPlot:
            td = plots.timeDeltas[plots.currentDelta]
            dbdata = db.read_data(td)
            plotStr, plotHeight = plots.make_plots_mpl(dbdata, td)

    cronTasks = cron.get_cron_tasks() if supply.wantCronTable else {}

    templateData = dict(
        viewstates=viewstates,
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
        inPinsFromArduino=supply.inPinsFromArduino,
        inPinsFromRaspberry=supply.inPinsFromRaspberry,
        gaugePins=supply.gaugePins,
        wantPlot=wantPlot, plotStr=plotStr, plotHeight=plotHeight,
        plotDeltas=plots.timeDeltas, currentPlotDelta=plots.currentDelta,
        yrange=plots.yrange,
        cameraDeltas=camera.timeDeltas, currentCameraDelta=camera.currentDelta,
        messages=messages, messageTimes=messageTimes,
        version=__version__)
    return render_template('aquarium.html', **templateData)


@app.route("/camera")
def stream():
    return Response(camera.generate_frame(), mimetype=camera.mimetype)


if __name__ == "__main__":
    if supply.isTest:
        print(u"╔═════════════════════════════════════╗")
        print(u"║   Running in test mode! (no GPIO)   ║")
        print(u"╚═════════════════════════════════════╝")
        print()
    logging.info('The app has started')
    app.run(host='0.0.0.0', port=80, debug=False)
