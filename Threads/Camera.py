import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
import time

from Drivers.camera import Camera


def thread(inqueue, outqueue):
    """
    摄像头线程，实现向指定队列中添加图片
    """
    camera = Camera()
    camera.open()
    try:
        while True:
            try:
                status = inqueue.get(timeout=0.1)
                if status == 'start':
                    break
            except Exception as e:
                continue
    except Exception as e:
        logging.error(e)

    try:
        while True:
            frame = camera.capture()

            try:
                if outqueue.full():
                    outqueue.get()
                outqueue.put([frame, time.time()], timeout=0.1)
            except Exception as e:  
                logging.error(e)

    except Exception as e:
        print(e)
    finally:
        camera.close()

        
