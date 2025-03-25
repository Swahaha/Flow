import RPi.GPIO as GPIO
import time
import numpy as np

GPIO.setmode(GPIO.BCM)
servo_pin = 18
GPIO.setup(servo_pin, GPIO.OUT)

pwm = GPIO.PWM(servo_pin, 50)  # 50Hz PWM
pwm.start(0)

def set_servo_duty_cycle(pulse_ms):
    duty = (pulse_ms / 20.0) * 100
    pwm.ChangeDutyCycle(duty)

try:
    for i in range(10):
        pw = float(input("Enter speed: ").strip())
        t = float(input("Enter duration: ").strip())
        print(f"Trying pulse width: {pw} ms")
        time.sleep(t)
        set_servo_duty_cycle(pw)
        time.sleep(0.3)
        set_servo_duty_cycle(0)
finally:
    pwm.stop()
    GPIO.cleanup()