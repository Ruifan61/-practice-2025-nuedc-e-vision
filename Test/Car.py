import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time

from Drivers.CarControl import CarControl, SERIAL_ID


def main():
    car = CarControl(SERIAL_ID)

    # car.send_angle(100, 50)
    # time.sleep(1)
    # car.send_none()
    # time.sleep(1)
    car.send_speed(-50, -50)
    # time.sleep(5)
    # car.send_none()
    # time.sleep(1)
    # car.send_off()

if __name__ == '__main__':
    main()
