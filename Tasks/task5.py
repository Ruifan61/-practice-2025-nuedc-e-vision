import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import time

from Drivers.CarControl import CarControl, SERIAL_ID
from Drivers.Laser import Laser 
from Algorithm.CenterGet import CenterGet
from Algorithm.configs import BASE_POINT


# BASE_POINT = (285, 192)     # Laser point coordinates, 640*360 resolution only


def task(camera):
    start_time = time.time()

    laser = Laser(17)
    laser.off()
    
    car = CarControl(SERIAL_ID)
    deta_x = 0
    deta_y = 0

    try:
        while True:
            print(f'cost:{time.time() - start_time}s')
            start_time = time.time()
            # Get image frame
            try:
                frame = camera.capture()
            except:
                continue
            
            # Target detection
            center = CenterGet(frame)
            
            if center is not None:
                # Calculate deviations
                deta_x = BASE_POINT[0] - center[0]
                deta_y = BASE_POINT[1] - center[1]
                
                car.send_angle(deta_x, deta_y)
                print(deta_x, deta_y)
            
                
    except KeyboardInterrupt:
        print("Program interrupted manually")
    finally:
        # Clean up resources
        pass

    