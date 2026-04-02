# import cv2
# import time
# import argparse
# from picamera2 import Picamera2

# def camera_test():
#     """
#     test camera with video
#     """
#     # 初始化picamera2
#     picam2 = Picamera2()
#     config = picam2.create_video_configuration(
#         main={"size": (1920,1080), 'format': 'BGR888'},
#         lores={"size": (640, 480)},
#         display="main",
#         controls={"FrameRate": 60}
#     )
#     picam2.configure(config)
#     picam2.start()
#     number = 0
#     # 读取帧（转为OpenCV格式）
#     while True:
#         frame = picam2.capture_array()
#         # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
#         cv2.imshow("CSI Camera", frame)
#         print("Frame number:%d, time: %d", number, time.time())
#         number += 1
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     cv2.destroyAllWindows()


# def video_record_by_frame():
#     # 初始化picamera2
#     picam2 = Picamera2()
#     config = picam2.create_still_configuration(
#         main={"size": (640, 480)},
#         controls={"FrameRate": 30}
#     )
#     picam2.configure(config)
#     picam2.start()

#     # 设置视频编码格式
#     fourcc = cv2.VideoWriter_fourcc(*'XVID')
#     out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

#     while True:
#         # 读取一帧图像
#         frame = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_RGB2BGR)
#         # 显示图像
#         cv2.imshow('frame', frame)

#         # 写入视频文件
#         out.write(frame)

#         # 按 'q' 键退出
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     # 释放资源
#     out.release()
#     cv2.destroyAllWindows()

# def picture_record_by_click():
#     """
#     once click, get and save a frame
#     frame name is timestamp
#     """
#     # 初始化picamera2
#     picam2 = Picamera2()
#     config = picam2.create_still_configuration(
#         main={"size": (640, 480)},
#         controls={"FrameRate": 30}
#     )
#     picam2.configure(config)
#     picam2.start()
    
#     print("Press 's' to save a picture, 'q' to quit.")

#     while True:
#         # 读取一帧图像
#         frame = cv2.cvtColor(picam2.capture_array(), cv2.COLOR_RGB2BGR)

#         # 显示图像
#         cv2.imshow('frame', frame)

#         # 按 's' 键保存图片，按 'q' 键退出
#         key = cv2.waitKey(1) & 0xFF
#         if key == ord('s'):
#             timestamp = time.strftime("%m%d_%H%M%S")
#             cv2.imwrite(f'{timestamp}.jpg', frame)
#             print(f"Saved {timestamp}.jpg")
#         elif key == ord('q'):
#             break

#     # 释放资源
#     cv2.destroyAllWindows()

# def main():
#     """
#     main function
#     """
#     parser = argparse.ArgumentParser(description="camera test")
#     parser.add_argument("--task", type=str, default="video_record_by_frame", help="task name")
#     args = parser.parse_args()
#     task_name = args.task

#     if task_name == "video_record_by_frame":
#         video_record_by_frame()
#     elif task_name == "picture_record_by_click":
#         picture_record_by_click()
#     elif task_name == "camera_test":
#         camera_test()
#     else:
#         print("task name error")


# if __name__ == "__main__":
#     main()

#——————————————————————————————————————没有显示出画面（帧率可以拉满）
# import sys
# import time
# import cv2
# from picamera2 import Picamera2

# try:
#     try:
#         from picamera2.preview import DrmPreview
#     except ImportError:
#         from picamera2.previews import DrmPreview
# except ImportError:
#     print("未找到 picamera2 预览模块")
#     sys.exit(1)

# FRAME_SIZE = (640, 480)
# TARGET_FPS = 60
# ENABLE_PREVIEW = False 

# def camera_test():
#     picam2 = Picamera2()

#     config = picam2.create_video_configuration(
#         main={"size": FRAME_SIZE, "format": "BGR888"}
#     )
#     picam2.configure(config)

#     # 设置硬件帧率
#     picam2.set_controls({"FrameRate": TARGET_FPS})

#     if ENABLE_PREVIEW:
#         picam2.start_preview(DrmPreview())

#     picam2.start()

#     print(f"CSI Camera 捕获已启动 (目标: {TARGET_FPS} FPS). 按 Ctrl+C 退出.")

#     # 帧率计算变量
#     last_time = time.time()
#     frame_count = 0

#     try:
#         while True:
#             # 捕获图像数据（但不显示）
#             frame = picam2.capture_array()
            
#             # 帧数累加
#             frame_count += 1
#             current_time = time.time()
#             elapsed = current_time - last_time

#             # 每隔 1 秒在终端打印一次实时帧率
#             if elapsed >= 1.0:
#                 real_fps = frame_count / elapsed
#                 print(f"\r当前实时帧率: {real_fps:.2f} FPS", end="")
                
#                 # 重置计数器
#                 frame_count = 0
#                 last_time = current_time

#     except KeyboardInterrupt:
#         print("\n\n正在安全关闭...")

#     finally:
#         picam2.stop()
#         # 移除了 cv2.destroyAllWindows()，因为没有开启窗口

# if __name__ == "__main__":
#     camera_test()

import sys
import time
import cv2
import numpy as np
from picamera2 import Picamera2

try:
    try:
        from picamera2.preview import DrmPreview
    except ImportError:
        from picamera2.previews import DrmPreview
except ImportError:
    print("未找到 picamera2 预览模块")
    sys.exit(1)

# ==========================================
# 全局配置
# ==========================================
FRAME_SIZE = (640, 480)
TARGET_FPS = 60
# 必须设为 True，否则 HDMI 没输出
ENABLE_PREVIEW = True 

class CameraApp:
    def __init__(self):
        self.picam2 = Picamera2()
        self.frame_count = 0
        self.last_time = time.time()
        self.is_running = True

    def _process_callback(self, request):
        """
        相机每捕获到一帧，都会在独立线程里自动调用这个函数
        """
        start_time = time.perf_counter()
        
        # 1. 获取 YUV 数据 (内存地址与 DRM 预览共享)
        yuv_data = request.make_array("main")
        
        # -----------------------------------------------------
        # [预留：在此处添加 YUV 绘图/识别逻辑]
        # 示例：在画面中心点一个白点（验证链路是否跑通）
        # h, w = FRAME_SIZE
        # yuv_data[h//2 : h//2+5, w//2 : w//2+5] = 255 
        # -----------------------------------------------------

        # 2. 帧率统计
        self.frame_count += 1
        now = time.time()
        elapsed = now - self.last_time
        if elapsed >= 1.0:
            fps = self.frame_count / elapsed
            print(f"\r当前处理帧率: {fps:.2f} FPS | 延迟: {(time.perf_counter()-start_time)*1000:.2f}ms", end="")
            self.frame_count = 0
            self.last_time = now

    def run(self):
        # 1. 配置 YUV420 格式（这是 DRM 预览性能最好的格式）
        config = self.picam2.create_video_configuration(
            main={"size": FRAME_SIZE, "format": "YUV420"}
        )
        self.picam2.configure(config)

        # 2. 注册回调函数
        self.picam2.post_callback = self._process_callback

        # 3. 设置硬件参数
        self.picam2.set_controls({
            "FrameRate": TARGET_FPS,
            "AeEnable": True
        })

        # 4. 启动预览与相机
        if ENABLE_PREVIEW:
            # DrmPreview 会直接接管 HDMI 输出
            self.picam2.start_preview(DrmPreview())
        
        self.picam2.start()
        print(f"服务已启动 | 分辨率: {FRAME_SIZE} | 目标: {TARGET_FPS}FPS")
        print("提示：此模式下画面直接输出至 HDMI，无需 cv2.imshow。")
        print("按下 Ctrl+C 退出...")

        try:
            # 主线程进入死循环，保持程序运行
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止...")
        finally:
            self.picam2.stop()

if __name__ == "__main__":
    app = CameraApp()
    app.run()