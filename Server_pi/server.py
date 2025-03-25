from flask import Flask, Response, request
from picamera2 import Picamera2
import cv2
import RPi.GPIO as GPIO
import time

# Servo Setup
GPIO.setmode(GPIO.BCM)
SERVO_PIN = 18
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)   # 50Hz PWM
pwm.start(0)

# Flask Setup
app = Flask(__name__)
picam2 = Picamera2()
# Reduce resolution of camera instead of cropping
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}, raw={"size": (1640, 1232)}))
picam2.start()

def gen_frames():
    while True:
        frame = picam2.capture_array()
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/run-servo', methods=['POST'])
def run_servo():
    try:
        data = request.get_json()
        pw = float(data.get("pw", 0))
        delay = float(data.get("delay", 0))
        
        time.sleep(delay)
        pwm.ChangeDutyCycle(pw)
        
        time.sleep(0.3)
        pwm.ChangeDutyCycle(0)
        return {"status": "servo triggered", "pw": pw, "delay": delay}
    
    except Exception as e:
        print("Error:", e)
        return {"error": str(e)}, 400

@app.route('/')
def index():
    return "Pi camera stream + servo control online."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)