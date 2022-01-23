ArdquariumPi
============

The goal of this project is to build a control system that runs several
aquarium devices based on a schedule, gauge values or user input. It provides
a web interface that LAN devices (optionally, remote devices) can access in
a browser.

<p align="center">
  <img src="docs/images/ArdquariumPi.png " width=1000 />
</p>

Features
========

GUI
---

The main program runs on a Raspberry Pi in Python and uses Flask. The main
display elements -- switches and gauges -- fit a vertical phone screen. All
other less critical display elements, such as plots, are added on a side to
sweep the web page sideways.

Hardware
--------

The relays are connected to a Raspberry Pi, while the gauges are connected to
an Arduino. Both devices are mutually supervised: the Raspberry Pi sends alarm
emails if it does not read from the Arduino, and the Arduino connects to a
phone via BLE and sends alarm texts by SMS if it does not detect the Raspberry
Pi. Optionally, gauges can be connected directly to the same Raspberry Pi.

Several temperature gauges provide input to the thermostat function.

An optional Raspberry Pi camera provides still pictures or a video stream
displayed in the web GUI.

An optional phone located close to the Arduino can be connected via BLE and
send alarm texts. The same phone can be used a standard control screen.

Software
--------

* Gauges are configured by the user in a separate Python module by following
  the supplied example.

* The main Arduino script as well as several test scripts for many devices are
  provided.

* The system state is saved in a database managed by SQLite.

* A time schedule of device operations is managed by `crontab` -- a Linux job
  scheduler. Setup instructions and an example are provided. The crontab table
  is visible by the web GUI and the coming events are displayed there.

* A phone connected to the Arduino via BLE runs an app developed in MIT App
  Inventor. The source code of the app is provided.

* The ArdquariumPi web server understands web hooks. For example, an ifttt.com
  applet can receive a trigger from Google Assistant processing a voice command
  "switch aquarium light on" and then it sends a web request to ArdquariumPi
  that activates the corresponding GPIO pin.

Documentation
-------------

See detailed instructions [here](https://kklmn.github.io/ArdquariumPi/).
