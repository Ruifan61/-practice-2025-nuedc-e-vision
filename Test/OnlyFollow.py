import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import time

from Drivers.camera import Camera
from Drivers.CarControl import CarControl, SERIAL_ID
from Drivers.Laser import Laser 
from Algorithm.CenterGet import CenterGet


BASE_POINT = (291, 192)     # Laser point coordinates, 640*360 resolution only


def task():
    start_time = time.time()

    laser = Laser(17)
    laser.on()

    cap = Camera()
    if not cap.open():
        print("Failed to open camera")
        return

    car = CarControl(SERIAL_ID)
    
    try:
        while True:
            # Get image frame
            
            frame = cap.capture()
            if frame is None:
                print("Failed to get image frame")
                time.sleep(0.01)
                continue
            
            # Target detection
            center = CenterGet(frame)
            
            if center is not None:
                # Calculate deviations
                print(f'cost:{time.time() - start_time}s')
                start_time = time.time()
                deta_x = BASE_POINT[0] - center[0]
                deta_y = BASE_POINT[1] - center[1]
                car.send_angle(deta_x, deta_y)
                print(deta_x, deta_y)
                center = None
            else:
                continue
                car.send_speed(200, 0)
                

            # if time.time() - start_time > 3.8 and center is not None:
            #     laser.on()
            #     print("Laser on: %.4f" % (time.time() - start_time))
            #     while True:
            #         time.sleep(1)
            

    except KeyboardInterrupt:
        print("Program interrupted manually")
    finally:
        # Clean up resources
        cap.close()

if __name__ == '__main__':
    # Start main program
    task()
    