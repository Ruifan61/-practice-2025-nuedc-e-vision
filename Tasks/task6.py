import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import time

from Drivers.CarControl import CarControl, SERIAL_ID
from Drivers.Laser import Laser 
from Algorithm.CenterGet import CenterGet
from Algorithm.CircleGet import CircleGet
from Algorithm.configs import BASE_POINT, BASE_TIME


# BASE_POINT = (285, 192)     # Laser point coordinates, 640*360 resolution only
# BASE_TIME = 20           # 绕圈的时间

def task(camera):
    start_time = time.time()

    laser = Laser(17)
    laser.on()
    
    car = CarControl(SERIAL_ID)
    deta_x = 0
    deta_y = 0

    try:
        while True:
            # print(f'cost:{time.time() - start_time}s')
            # start_time = time.time()
            # Get image frame
            try:
                frame = camera.capture()
            except:
                continue
            
            # Target detection
            results = CenterGet(frame, return_pts=True)
            print(results)
            
            if results is not None:
                # Get the center of the target
                center = results[0]
                pts = results[1]
                Circle = CircleGet()

                circle_points = Circle.forward(center, pts)

                current_step = (time.time() - start_time)/BASE_TIME*len(circle_points)
                # target取最近两个整数的加权平均
                # target = circle_points[int(current_step-1)] * (current_step - int(current_step)) + circle_points[int(current_step)] * (int(current_step) + 1 - current_step)
                target = circle_points[int(current_step)]
                # Calculate deviations
                deta_x = BASE_POINT[0] - target[0]
                deta_y = BASE_POINT[1] - target[1]
                
                car.send_angle(deta_x, deta_y)
                print(deta_x, deta_y)
            
                
    except KeyboardInterrupt:
        print("Program interrupted manually")
        
    finally:
        # Clean up resources
        laser.off()
        car.send_angle(0, 0)

    