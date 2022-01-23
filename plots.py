# -*- coding: utf-8 -*-
__author__ = "Konstantin Klementiev"
__date__ = "11 Jan 2022"

isTest = False  # put True for running this module as main

import os.path as osp
import base64
from io import BytesIO
import matplotlib as mpl
# import matplotlib.pyplot as plt
if isTest:
    from matplotlib.pyplot import figure as Figure
else:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib import gridspec
import datetime
from collections import OrderedDict

import supply

timeDeltas = OrderedDict([
    (u"½h", {'minutes': 30}), ("4h", {'hours': 4}), ("1d", {'days': 1}),
    ("1w", {'days': 7}), ("1m", {'days': 30}), ("6m", {'days': 180}),
    ("all", None)])
# currentdelta = u"½h"
currentDelta = "4h"
# yrange = "user"  # can be "auto"
yrange = "auto"  # can be "user"

ioKeys = (list(supply.outPins.keys()) +
          list(supply.inPinsFromRaspberry.keys()) +
          list(supply.inPinsFromArduino.keys()))
ioValues = (list(supply.outPins.values()) +
            list(supply.inPinsFromRaspberry.values()) +
            list(supply.inPinsFromArduino.values()))
pColors = [rec['color'] for rec in ioValues if 'color' in rec]
tColors = [rec['color'] for rec in supply.temperatures.values()]
aColors = [rec['color'] for rec in supply.sensorsFromArduino.values()]
rColors = [rec['color'] for rec in supply.sensorsFromRaspberry.values()]
tNames = list(supply.temperatures.keys())
aNames = list(supply.sensorsFromArduino.keys())
rNames = list(supply.sensorsFromRaspberry.keys())
aUnits = [rec['unit'] for rec in supply.sensorsFromArduino.values()]
rUnits = [rec['unit'] for rec in supply.sensorsFromRaspberry.values()]
aLimits = [rec['limits'] for rec in supply.sensorsFromArduino.values()]
rLimits = [rec['limits'] for rec in supply.sensorsFromRaspberry.values()]

lw = 0.5  # linewidth
ms = 1.0  # markersize
alpha = 0.5

facecolor = '#444'
spinecolor = '#eee'
cssName = osp.join(
    osp.dirname(osp.abspath(__file__)), 'static', 'css', 'main.css')
inComment = 0
with open(cssName, 'r') as f:
    for line in f.readlines():
        if '/*' in line:
            inComment += 1
        if '*/' in line:
            inComment -= 1
        if inComment:
            continue

        pos = line.find("--color-bright-text:")
        if pos > -1:
            spinecolor = line[line.find(":")+1: line.find(";")].strip()
        pos = line.find("--color-panel:")
        if pos > -1:
            facecolor = line[line.find(":")+1: line.find(";")].strip()
if len(facecolor) == 4:
    facecolor = '#' + ''.join(i*2 for i in facecolor[1:])
if len(spinecolor) == 4:
    spinecolor = '#' + ''.join(i*2 for i in spinecolor[1:])


def versiontuple(v):
    a = v.split(".")
    return tuple(map(int, [''.join(c for c in s if c.isdigit()) for s in a]))


def color_text(x, y, strings, states, colors, ax, **kwargs):
    t = ax.transAxes
    canvas = ax.figure.canvas
    for s, st, c in zip(strings, states, colors):
        weight = 'heavy' if st else 'normal'
        text = ax.text(x, y, s, color=c, transform=t, weight=weight, **kwargs)
        # Need to draw to update the text position.
        text.draw(canvas.get_renderer())
        ex = text.get_window_extent()
        t = mpl.transforms.offset_copy(
            text.get_transform(), x=ex.width, units='dots')


def make_plots_mpl(data, timeDeltaDict=None):
    times = [d[0] for d in data]

    nTplot = 1 + ((len(supply.temperatures)-1) // 2)
    nax = len(aNames) + len(rNames)

    plotWidth = 3.6
    plotHeight = 0.8 * (len(aNames) + len(rNames) + nTplot)
    minPlotHeight = len(supply.outPins) * 0.42  # inch
    plotHeight = max(plotHeight, minPlotHeight)
    dpi = 100
    fig = Figure(figsize=(plotWidth*1.6, plotHeight*1.6), dpi=dpi)
    fig.set_facecolor(facecolor)
    if not isTest:
        canvas = FigureCanvasAgg(fig)  # noqa

    kw = {}
    if versiontuple(mpl.__version__) >= versiontuple("2.0.0"):
        kw['facecolor'] = facecolor
    else:
        kw['axisbg'] = facecolor
    gs = gridspec.GridSpec(
        nax+2, 1, height_ratios=[2*nTplot]+[2 for i in range(nax)]+[1])
    ax0 = fig.add_subplot(gs[0], **kw)
    axi = [fig.add_subplot(gs[i], sharex=ax0, **kw) for i in range(1, nax+2)]
    for ax in [ax0] + axi:
        for spine in ['bottom', 'top', 'left', 'right']:
            ax.spines[spine].set_color(spinecolor)
        ax.xaxis.label.set_color(spinecolor)
        ax.yaxis.label.set_color(spinecolor)
        ax.tick_params(axis='x', colors=spinecolor)
        ax.tick_params(axis='y', colors=spinecolor)

    tp = dict(bottom=True, top=True, labelbottom=False)
    for ax in axi:
        ax.tick_params(axis="x", labeltop=False, **tp)
    ax0.tick_params(axis="x", labeltop=True, **tp)
    axi[-1].set_xlabel(u'date time', fontsize=13)

    axt = ax0  # temperature axes
    axs = axi[-1]  # state axes
    axd = axi[:-1]  # other sensor axes
    axNames = ['temperature'] + aNames + rNames + ['ios']
    axUnits = [supply.temperatureUnit] + aUnits + rUnits + ['']

    for it, color in enumerate(tColors):
        datat = [d[it+2] for d in data]
        lo = supply.temperatureOutlierLimits
        times0 = [t for t, d in zip(times, datat) if lo[0] < d < lo[1]]
        datat0 = [d for t, d in zip(times, datat) if lo[0] < d < lo[1]]
        # td = [(t, d) for t, d in zip(times, datat) if lo[0] < d < lo[1]]
        # times0, datat0 = zip(*td)
        axt.plot(times0, datat0, 'o-', lw=lw, color=color, alpha=alpha,
                 ms=ms, markeredgecolor=color)

    for it, (ax, color) in enumerate(zip(axd, aColors+rColors)):
        datao = [d[it+2+len(tNames)] for d in data]
        ax.plot(times, datao, 'o-', lw=lw, color=color, alpha=alpha,
                ms=ms, markeredgecolor=color)

    ioNames = supply.plotPins
    onVals = [1.15-i*0.1 for i in range(len(ioNames))]
    ioColors = []
    ioDisplayed = []
    ioState = []
    for name, onVal in zip(ioNames, onVals):
        if name in ioKeys:
            ioDisplayed.append(name)
            iio = ioKeys.index(name)
            dataIO = [onVal if d[1] & 2**iio else 1-onVal for d in data]
            ioState.append(1 if dataIO[-1] > 0.5 else 0)
            color = pColors[iio]
            ioColors.append(color)
            axs.plot(times, dataIO, 'o-', lw=lw, color=color, alpha=alpha,
                     ms=ms, markeredgecolor=color)

    if timeDeltaDict is not None:
        now = datetime.datetime.now()
        ax0.set_xlim([now-datetime.timedelta(**timeDeltaDict), now])

    if yrange == "user":
        axt.set_ylim(supply.temperatureDisplayLimits)
    elif yrange == "auto":
        axt.set_ylim([None, None])
    axs.set_ylim(-0.2, 1.2)
    axs.set_yticks([0, 1])
    axs.set_yticklabels(['off', 'on'])
    for ax, lims in zip(axd, aLimits+rLimits):
        if yrange == "user":
            ax.set_ylim(*lims)
        elif yrange == "auto":
            ax.set_ylim([None, None])

    # fig.autofmt_xdate()
    fig.canvas.draw()
    if versiontuple(mpl.__version__) < versiontuple("2.0.0"):
        tlabels = [item.get_text() for item in axi[-1].get_xticklabels()]
        posdot = tlabels[0].find('.0')
        if posdot > 0:
            tlabels = [item[:posdot] for item in tlabels]
            axi[-1].set_xticklabels(tlabels)
    fig.subplots_adjust(
        left=0.09, bottom=0.04, right=0.98, top=0.94, hspace=0.04)

    for ax, name, unit in zip([ax0]+axi, axNames, axUnits):
        label = u'{0} ({1})'.format(name, unit) if unit else name
        if name == 'ios':
            color_text(0.01, 0.65, ioDisplayed, ioState, ioColors, ax,
                       va='top', fontsize=13, alpha=0.7)
        else:
            ax.text(0.01, 0.95, label, transform=ax.transAxes, va='top',
                    fontsize=13, color=spinecolor, alpha=0.7)

    if timeDeltaDict is not None:
        ax0.annotate(
            '', xy=(1, 1), xycoords='axes fraction', xytext=(1, 1.25),
            textcoords='axes fraction', arrowprops=dict(
                color=spinecolor, width=1, headwidth=7, headlength=10))
    fig.text(0.01, 0.01, '{0} time points'.format(len(times)),
             color=spinecolor, alpha=0.25)

    xticklabels = ax0.get_xticklabels()
    ax0.set_xticklabels(xticklabels[:-1], rotation=20, ha="left")

    if isTest:
        fig.show()
    else:
        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor=facecolor)
        return (base64.b64encode(buf.getvalue()).decode("ascii"),
                plotHeight*dpi)


if __name__ == "__main__":
    import db
    dbdata = db.read_data()
    make_plots_mpl(dbdata)
    print("Done")
