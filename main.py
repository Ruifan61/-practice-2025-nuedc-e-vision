import threading
import queue

from Threads.Camera import thread as camera_thread
from Threads.UI import thread as ui_thread
from Threads.Button import thread as button_thread

from Tasks.task1 import task as task1
from Tasks.task2 import task as task2
from Tasks.task3l import task as task3L
from Tasks.task3r import task as task3R
from Tasks.task4 import task as task4
from Tasks.task5 import task as task5
from Tasks.task6 import task as task6

from Drivers.Laser import Laser
from Drivers.camera import Camera


if __name__ == '__main__':
    # 关闭激光笔
    laser = Laser(17)
    laser.off()

    camera = Camera()
    camera.open()

    # img_start_queue = queue.Queue(maxsize=1)    # (str)start
    # img_queue = queue.Queue(maxsize=3)          # [img, time.time()]
    button_queue = queue.Queue(maxsize=1)       # [action, time.time()]
    taskid_queue = queue.Queue(maxsize=1)       # (int)taskid

    current_task = 0

    # camera_thread = threading.Thread(target=camera_thread, args=(img_start_queue,img_queue,))
    button_thread = threading.Thread(target=button_thread, args=(button_queue,))
    ui_thread = threading.Thread(target=ui_thread, args=(taskid_queue,))

    # camera_thread.start()
    # print("Camera thread started")
    button_thread.start()
    print("Button thread started")
    ui_thread.start()
    print("UI thread started")

    try:
        while True:
            if not button_queue.empty():
                action = button_queue.get()
                if action[0] == "shortPress":
                    current_task = (current_task+1)%7
                    taskid_queue.put(current_task)
                    print(current_task)
                elif action[0] == "longPress":
                    taskid_queue.put(-1)
                    # button_thread.join()
                    # ui_thread.join()
                    # img_start_queue.put("start")
                    # 执行对应任务
                    # if current_task == 0:
                    #     print("run task 1")
                    #     task1(camera)
                    if current_task == 1:
                        print("run task 2")
                        task2(camera)
                    elif current_task == 2:
                        print("run task 3L")
                        task3L(camera)
                    elif current_task == 3:
                        print("run task 3R")
                        task3R(camera)
                    elif current_task == 4:
                        print("run task 4")
                        task4(camera)
                    elif current_task == 5:
                        print("run task 5")
                        task5(camera)
                    elif current_task == 6:
                        print("run task 6")
                        task6(camera)
                    else:
                        pass
                

    except KeyboardInterrupt:
        # camera_thread.join()
        button_thread.join()
        ui_thread.join()
        print("All threads joined")