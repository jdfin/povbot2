from flask import Flask, render_template, request, Response
import threading
import RPi.GPIO as GPIO
import io
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform
import logging
from flask_cors import CORS
from threading import Condition
app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

GPIO.setmode(GPIO.BCM)

# right

GPIO.setup(12, GPIO.OUT)
pwm_r = GPIO.PWM(12, 1000)
pwm_r.stop()

speed_r = 50
fwd_r = 50
rev_r = 50

GPIO.setup(6, GPIO.OUT)
GPIO.output(6, GPIO.LOW)

GPIO.setup(5, GPIO.OUT)
GPIO.output(5, GPIO.LOW)

# left

GPIO.setup(13, GPIO.OUT)
pwm_l = GPIO.PWM(13, 1000)
pwm_l.stop()

speed_l = 75
fwd_l = 75
rev_l = 75

GPIO.setup(16, GPIO.OUT)
GPIO.output(16, GPIO.LOW)

GPIO.setup(19, GPIO.OUT)
GPIO.output(19, GPIO.LOW)

def forward():
    global speed_r
    global speed_l
    # right forward
    GPIO.output(6, GPIO.LOW)
    GPIO.output(5, GPIO.HIGH)
    speed_r = fwd_r
    pwm_r.start(speed_r)
    # left forward
    GPIO.output(16, GPIO.LOW)
    GPIO.output(19, GPIO.HIGH)
    speed_l = fwd_l
    pwm_l.start(speed_l)

def reverse():
    global speed_r
    global speed_l
    # right reverse
    GPIO.output(5, GPIO.LOW)
    GPIO.output(6, GPIO.HIGH)
    speed_r = rev_r
    pwm_r.start(speed_r)
    # left reverse
    GPIO.output(19, GPIO.LOW)
    GPIO.output(16, GPIO.HIGH)
    speed_l = rev_l
    pwm_l.start(speed_l)

def stop():
    global speed_r
    global speed_l
    # right stop
    speed_r = 0
    pwm_r.stop()
    GPIO.output(6, GPIO.LOW)
    GPIO.output(5, GPIO.LOW)
    # left stop
    speed_l = 0
    pwm_l.stop()
    GPIO.output(16, GPIO.LOW)
    GPIO.output(19, GPIO.LOW)

def right():
    global speed_r
    global speed_l
    if speed_r == 0 and speed_l == 0:
        # not moving - rotate
        # right forward
        pwm_r.stop()
        GPIO.output(5, GPIO.LOW)
        GPIO.output(6, GPIO.HIGH)
        speed_r = fwd_r
        pwm_r.start(speed_r)
        # left reverse
        pwm_l.stop()
        GPIO.output(16, GPIO.LOW)
        GPIO.output(19, GPIO.HIGH)
        speed_l = rev_l
        pwm_l.start(speed_l)
    else:
        # moving - curve right a little
        speed_r -= 5
        if (speed_r < 0):
            speed_r = 0
        pwm_r.start(speed_r)
        speed_l += 5
        if (speed_l > 100):
            speed_l = 100
        pwm_l.start(speed_l)

def left():
    global speed_r
    global speed_l
    if speed_r == 0 and speed_l == 0:
        # not moving - rotate
        # right reverse
        pwm_r.stop()
        GPIO.output(6, GPIO.LOW)
        GPIO.output(5, GPIO.HIGH)
        speed_r = rev_r
        pwm_r.start(speed_r)
        # left forward
        pwm_l.stop()
        GPIO.output(19, GPIO.LOW)
        GPIO.output(16, GPIO.HIGH)
        speed_l = rev_l
        pwm_l.start(speed_l)
    else:
        # moving - curve left a little
        speed_r += 5
        if (speed_r > 100):
            speed_r = 100
        pwm_r.start(speed_r)
        speed_l -= 5
        if (speed_l < 0):
            speed_l = 0
        pwm_l.start(speed_l)

@app.route('/key', methods=['GET'])
def get_key():
    key = request.args.get('key')
    if key:
        print(f'Key Pressed: {key}')
        # Check which key is pressed and set GPIO pins accordingly
        if key == 'W':
            forward()
        elif key == 'A':
            left()
        elif key == 'S':
            stop()
        elif key == 'D':
            right()
        elif key == 'X':
            reverse()
    return '', 200

# I can't get '/' instead of '/home' to work :(
@app.route('/home')
def index():
    """Video streaming home page."""
    return render_template('index.html')

def gen():
    """Video streaming generator function."""
    with Picamera2() as camera:
        camera.configure(camera.create_video_configuration(
            main={"size": (1640, 1232)}, transform=Transform(vflip=1, hflip=1)))
        output = StreamingOutput()
        camera.start_recording(JpegEncoder(), FileOutput(output))
        try:
            while True:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        finally:
            camera.stop_recording()

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, threaded=True)
