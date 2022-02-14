# -*- coding: utf-8 -*-
__author__ = "Konstantin Klementiev"
__date__ = "8 Jan 2022"

import threading
from collections import OrderedDict
import distro
import numpy as np
import datetime

enabled = True
if enabled:
    import cv2


if distro.id().startswith('ras') and enabled:
    # I am on a RPi, cv2.VideoCapture(0) doesn't work
    from subprocess import Popen, PIPE
    if int(distro.version()) >= 11:  # starting from Bullseye
        prog = "libcamera-vid"
    else:  # Buster and below
        prog = "raspivid"
    device = "tcp://0.0.0.0:8888"  # for cv2.VideoCapture(device)
    runStr = "{0} -t 0 --inline --listen -n -o {1}".format(prog, device)
    print('running "{0}"'.format(runStr))
    pipe = Popen(runStr, shell=True, stdout=PIPE, stderr=PIPE)
    # pipe.communicate()  # don't run it, it blocks
else:
    device = 0  # for cv2.VideoCapture(device)
    # device = "tcp://192.168.1.70:8888"  # for cv2.VideoCapture(device)

timeDeltas = OrderedDict([
    ("video 3s", {'seconds': 3}), ("video 10s", {'seconds': 10}),
    ("video 30s", {'seconds': 30}), ("still image", None)])
# currentDelta = "video 3s"
currentDelta = "still image"

boundary = "aquariumCameraFrame"  # any unique str
mimetype = "multipart/x-mixed-replace; boundary={0}".format(boundary)


class Streamer:
    processing = (
        # ('resize', [(640, 480)]),  # good for horizontal image
        ('resize', [(480, 360)]),  # good for vertical image
        ('rotate', [270]),  # deg, 270="rotate right"
        # ('detect_motion', [10, (255, 0, 0)]),  # bkgndTargetCount, colorBGR
        ('add_time_stamp', ['%Y/%m/%d, %H:%M:%S', (0, 0, 255)]),  # fmt, cBGR
        ('encode', ['.jpg']),  # must be encoded
    )
    cameraNotFoundImage = 'static/_images/RPiCamera.png'

    def __init__(self):
        self.currentFrame = None
        self.cameraAvailable = None
        self.bkgnd = None
        self.bkgndCount = 0
        self.contentType = 'jpeg'
        self.vs = cv2.VideoCapture(device)

    def device_available(self):
        return (self.vs is not None) and self.vs.isOpened()

    def update_bkgnd(self, gray, alpha=0.5):
        if self.bkgnd is None:
            self.bkgnd = gray.copy().astype("float")
        else:
            cv2.accumulateWeighted(gray, self.bkgnd, alpha=alpha)

    def motion_rect(self, gray, thresh=25):
        if currentDelta.startswith("s"):
            return
        delta = cv2.absdiff(self.bkgnd.astype("uint8"), gray)
        _, binary = cv2.threshold(delta, thresh, 255, cv2.THRESH_BINARY)
        binary = cv2.erode(binary, None, iterations=2)
        binary = cv2.dilate(binary, None, iterations=2)
        cnts, _ = cv2.findContours(binary.copy(), cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
        if len(cnts) == 0:
            return
        minX, minY = np.inf, np.inf
        maxX, maxY = -np.inf, -np.inf
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            minX, minY = min(minX, x), min(minY, y)
            maxX, maxY = max(maxX, x+w), max(maxY, y+h)
        return minX, minY, maxX, maxY

    def rotate(self, frame, deg):
        quad = int(round(deg/90))
        if quad == 1:
            rotateCode = cv2.ROTATE_90_CLOCKWISE
        elif quad == 2:
            rotateCode = cv2.ROTATE_180
        elif quad == 3:
            rotateCode = cv2.ROTATE_90_COUNTERCLOCKWISE
        else:
            return frame
        return cv2.rotate(frame, rotateCode)

    def detect_motion(self, frame, bkgndTargetCount, color):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        if self.bkgndCount > bkgndTargetCount:
            rect = self.motion_rect(gray)
            if rect is not None:
                cv2.rectangle(frame, rect[:2], rect[2:], color, 3)
        self.update_bkgnd(gray)
        self.bkgndCount += 1
        return frame

    def resize(self, frame, size):
        return cv2.resize(frame, size)

    def add_time_stamp(self, frame, fmt, color):
        now = datetime.datetime.now()
        cv2.putText(frame, now.strftime(fmt), (5, frame.shape[0] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        if not self.cameraAvailable:
            cv2.putText(frame, 'no camera found', (5, 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        return frame

    def encode(self, frame, fmt):
        if fmt.endswith('jpg'):
            self.contentType = 'jpeg'  # not 'jpg'!
        elif fmt.endswith('png'):
            self.contentType = 'png'
        else:
            raise ValueError('unknown image encoding')
        flag, encodedImage = cv2.imencode(fmt, frame)
        if not flag:
            raise ValueError('encoding has failed')
        return encodedImage

    def get_frame(self):
        with lock:
            if not self.device_available():  # for hot camera insertion, in W10
                self.vs = cv2.VideoCapture(device)
            self.cameraAvailable, frame = self.vs.read()
            if not self.cameraAvailable:
                frame = cv2.imread(self.cameraNotFoundImage)
            for methName, args in self.processing:
                meth = getattr(self, methName)
                frame = meth(frame, *args)
            self.currentFrame = frame.copy()


if enabled:
    streamer = Streamer()
    lock = threading.Lock()


def generate_frame():
    if currentDelta.startswith("v"):
        tstart = datetime.datetime.now()
        tdelta = datetime.timedelta(**timeDeltas[currentDelta])

    while enabled:
        # don't use threading.Thread in Buster, as it quite soon fails:
        # Assertion fctx->async_lock failed at src/libavcodec/pthread_frame.c:155
        # frameThread = threading.Thread(target=streamer.get_frame)
        # frameThread.start()
        # frameThread.join()
        streamer.get_frame()
        yield (b'--' + boundary.encode() + b'\r\n' +
               b'Content-Type: image/' + streamer.contentType.encode() +
               b'\r\n\r\n' + bytearray(streamer.currentFrame) + b'\r\n')

        if not streamer.device_available():
            break
        if currentDelta.startswith("s"):
            break
        if datetime.datetime.now()-tstart > tdelta:
            break
