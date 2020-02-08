ArdquariumPi
============

ArdquariumPi is a collections of tools to run aquarium devices. It provides a
web interface that LAN devices can access in a browser.

It is operational, though not documented yet. The front control page will get
more features. Currently it looks like this:

<p align="center">
  <img src="doc/_images/ArdquariumPi0.png " width=1000 />
</p>

Main features
-------------

- The main program runs on Raspberry Pi in Python and uses Flask. It receives
  periodic measurements of analog and/or digital signals from Arduino. Arduino
  code is also included. Optionally, measurements can be directly managed by
  Raspberry Pi.

- Raspberry Pi and Arduino supervise each other. And this is the primary reason
  to work with two devices, not just with Raspberry Pi. At alarm conditions,
  the former sends e-mails while the latter connects via BLE to a dedicated
  phone that sends SMSes. A source code for the phone app is also included that
  needs `MIT App Inventor 2`.

- The measured signals are stored in a local database and are displayed as time
  plots on the front web page. The current values are displayed by color-coded
  gauges.

- Temperature is regulated by a thermostat function.

- Time-based device switching uses the `cron` utility. An example time table is
  provided. The scheduling information is also displayed on the front web page.

- Feeding function that puts to sleep a few defined devices for a given time
  interval.

- (not yet) Integration with Google Home for sending voice commands over LAN.

Dependencies
------------

croniter

How to run
----------

For a test on any computer, unzip into a suitable location (no `setup.py` is
provided because the user will need to modify a few files) and run
`python3 ardquariumPi.py`, maybe with `sudo`. Access the web interface as
`localhost` in your browser.

For a real run on a Raspberri Pi, unzip into a user-accessible location, e.g.
`ArdquariumPi` in the `pi` home, and edit `supply.py` (where at least set
`isTest = False`) and `__secret.py` . Edit and upload
`arduino/ardquarium/ardquarium.ino` into your arduino board if needed. Read
files in `autorun` folder and use them. Run `sudo python3 ardquariumPi.py`.
Access the web interface by the LAN address of the Raspberry Pi.
