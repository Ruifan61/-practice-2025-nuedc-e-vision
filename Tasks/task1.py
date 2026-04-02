import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import time

from Drivers.CarControl import CarControl, SERIAL_ID
from Drivers.Laser import Laser 
from Algorithm.CenterGet import CenterGet


def task(camera):
    laser = Laser(17)
    laser.on()