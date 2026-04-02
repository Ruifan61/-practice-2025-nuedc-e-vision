import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw, ImageFont
import time

from Drivers.SSD1306 import SSD1306_IIC


def thread(inqueue):
    """
    界面线程，在每行中间显示行号（0-6），以>为光标，初始情况下，光标在第0行
    """
    # 初始化显示屏
    display = SSD1306_IIC(1)
    display.clear()
    image = Image.new('1',(128,64),0)
    font = ImageFont.truetype('wqy-microhei.ttc',10)
    draw = ImageDraw.ImageDraw(image)
    draw.text((32 ,0 ), '>>>', fill=1, font=font)
    draw.text((64,0 ), 'TASK1', fill=1, font=font)
    draw.text((64,8 ), 'TASK2', fill=1, font=font)
    draw.text((64,16), 'TASK3L', fill=1, font=font)
    draw.text((64,24), 'TASK3R', fill=1, font=font)
    draw.text((64,32), 'TASK4', fill=1, font=font)
    draw.text((64,40), 'TASK5', fill=1, font=font)
    draw.text((64,48), 'TASK6', fill=1, font=font)
    display.renderPillowImage(image)

    current_task = 0

    try:
        while True:
            if not inqueue.empty():
                data = inqueue.get(timeout=0.1)
                if data != -1:
                    draw.rectangle([(32, current_task*8), (32+20, current_task*8+8)], fill=0)
                    current_task = data%7
                    draw.text((32,current_task*8), '>>>', fill=1, font=font)
                    display.renderPillowImage(image)
                elif data == -1:
                    display.clear()
                    while True:
                        time.sleep(1)
                        pass
                else:
                    pass
                

    except KeyboardInterrupt:
        display.close()
        print('UI thread exit')
