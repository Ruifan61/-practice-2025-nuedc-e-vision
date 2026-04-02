import time
from RPi import GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(22,GPIO.IN)

def readGPIO():
    return GPIO.input(22)

def thread(outqueue):
    timeCnt = 0
    while True:
        value = readGPIO()
        if value == 0:
            timeCnt += 1
        else:
            if timeCnt == 0:
                continue
            elif timeCnt < 10:
                try:
                    if outqueue.full():
                        outqueue.get()
                    outqueue.put(["shortPress", time.time()], timeout=0.1)
                except Exception as e:  
                    logging.error(e)
            else:
                try:
                    if outqueue.full():
                        outqueue.get()
                    outqueue.put(["longPress", time.time()], timeout=0.1)
                    while True:
                        time.sleep(1)
                except Exception as e:  
                    logging.error(e)
            timeCnt = 0

        time.sleep(0.05)
# 定义一个名为OLEDRendingTask的函数
def OLEDRendingTask():
    # 函数体为空，没有执行任何操作
    pass

if __name__ == '__main__':
    thread()