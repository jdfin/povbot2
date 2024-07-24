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
GPIO.setup(22, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)


GPIO.output(22, GPIO.LOW)
GPIO.output(23, GPIO.LOW)
GPIO.output(17, GPIO.LOW)
GPIO.output(27, GPIO.LOW)

def forward():
    GPIO.output(22, GPIO.LOW)  #left side
    GPIO.output(23, GPIO.HIGH)
    
    GPIO.output(17, GPIO.HIGH) #right side
    GPIO.output(27, GPIO.LOW)
    
def stop():
    GPIO.output(22, GPIO.LOW)  
    GPIO.output(23, GPIO.LOW)
    
    GPIO.output(17, GPIO.LOW) 
    GPIO.output(27, GPIO.LOW)
    
def right():
    GPIO.output(22, GPIO.LOW)  
    GPIO.output(23, GPIO.HIGH)
    
    GPIO.output(17, GPIO.LOW) 
    GPIO.output(27, GPIO.HIGH)
    
def left():
    GPIO.output(22, GPIO.HIGH)  
    GPIO.output(23, GPIO.LOW)
    
    GPIO.output(17, GPIO.HIGH) 
    GPIO.output(27, GPIO.LOW)



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
