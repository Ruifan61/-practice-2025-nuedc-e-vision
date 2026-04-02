import RPi.GPIO as GPIO
import time

def test():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.OUT)
    while True:
        GPIO.output(17, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(17, GPIO.LOW)
        time.sleep(1)

def laser_on():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.OUT)
    GPIO.output(17, GPIO.HIGH)


if __name__ == "__main__":
    laser_on()