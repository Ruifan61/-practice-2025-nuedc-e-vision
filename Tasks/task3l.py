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
    deta_history = 0
    laser_flag = False

    try:
        while True:
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

            else:
                car.send_speed(900, 0)
            

            if center is not None and abs(deta_x) < 5 and abs(deta_y) < 5:
                deta_history += 1
                if deta_history > 11:
                    laser.on()
                    time.sleep(0.001)
                    laser.off()
                    print("Task Over: %.4f" % (time.time() - start_time))

            # 时间快到了必须开激光得分
            if not laser_flag and (time.time() - start_time) > 3.8:
                laser.on();time.sleep(0.01);laser.off()
                laser_flag = True
            # 时间超出，关闭激光
            if (time.time() - start_time) > 5:
                laser.off()
                break
            

    except KeyboardInterrupt:
        print("Program interrupted manually")
    finally:
        # Clean up resources
        pass

    