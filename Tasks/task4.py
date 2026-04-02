import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import time

# from Drivers.CarControl import CarControl, SERIAL_ID
from Drivers.Laser import Laser 
from Algorithm.CenterGet import CenterGet
from Algorithm.configs import BASE_POINT

def task(camera):
    # 初始化统计变量
    frame_count = 0
    fps_start_time = time.time()
    
    laser = Laser(17)
    laser.on()
    
    # car = CarControl(SERIAL_ID)

    print("="*40)
    print("任务 4：高性能命令行模式")
    print("提示：已禁用所有窗口显示，算力全开")
    print("退出方式：按 Ctrl + C")
    print("="*40)

    try:
        while True:
            frame_count += 1
            frame = camera.capture()
            
            if frame is None:
                continue

            # --- 核心识别逻辑 ---
            # CLI 模式下不需要返回 pts 画图，直接拿中心即可
            center = CenterGet(frame, return_pts=False)
            
            if center is not None:
                # 计算偏差
                deta_x = BASE_POINT[0] - center[0]
                deta_y = BASE_POINT[1] - center[1]
                
                # 串口发送（如果已连车，取消注释）
                # car.send_angle(deta_x, deta_y)
                
                # 终端输出实时结果
                print(f"[DETECTED] Delta X: {deta_x:4d} | Delta Y: {deta_y:4d} | Center: {center}")
            
            # --- 性能监控打印 ---
            if frame_count >= 30:
                elapsed = time.time() - fps_start_time
                avg_fps = frame_count / elapsed
                # 使用 sys.stdout.write 实现在同一行刷新，避免刷屏
                #sys.stdout.write(f"\r实时运行中... 当前平均帧率: {avg_fps:.1f} FPS")
                sys.stdout.flush()
                
                frame_count = 0
                fps_start_time = time.time()
                
    except KeyboardInterrupt:
        print("\n\n检测到用户中断，正在安全退出...")
    finally:
        laser.off()
        # 命令行模式下不需要销毁窗口，但保留此行无副作用
        cv2.destroyAllWindows()
        print("激光已关闭，资源已释放")

if __name__ == '__main__':
    from Drivers.camera import Camera
    cam = Camera()
    if cam.open():
        task(cam)
    else:
        print("!!! 错误：摄像头启动失败，请检查供电或连接")