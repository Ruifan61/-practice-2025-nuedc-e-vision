#——————————————————————————————————————————————————————————————————————————
#————————————————————————————————USB（无画面，录制5s视频到本地）————————————————————————————————
#——————————————————————————————————————————————————————————————————————————

# import cv2
# import time

# def test_capture_only():
#     cap = cv2.VideoCapture(0, cv2.CAP_V4L2)   # 按需改成 1、2...

#     if not cap.isOpened():
#         print("open failed")
#         return

#     # 请求参数
#     cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#     cap.set(cv2.CAP_PROP_FPS, 60)

#     actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     actual_fps = cap.get(cv2.CAP_PROP_FPS)

#     fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
#     fourcc_str = "".join([chr((fourcc >> (8 * i)) & 0xFF) for i in range(4)])

#     print("=" * 60)
#     print(f"配置结果: {actual_w}x{actual_h} @ {actual_fps:.2f} FPS")
#     print(f"采集格式: {fourcc_str}")
#     print("开始纯采集测试 10 秒，不显示、不保存...")
#     print("=" * 60)

#     warmup_frames = 30
#     for _ in range(warmup_frames):
#         ret, _ = cap.read()
#         if not ret:
#             print("warmup failed")
#             cap.release()
#             return

#     test_seconds = 10
#     frame_count = 0
#     start_time = time.time()

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             print("read failed")
#             break

#         frame_count += 1

#         if time.time() - start_time >= test_seconds:
#             break

#     elapsed = time.time() - start_time
#     avg_fps = frame_count / elapsed if elapsed > 0 else 0.0

#     print("=" * 60)
#     print(f"测试时长: {elapsed:.3f} s")
#     print(f"总帧数: {frame_count}")
#     print(f"平均FPS: {avg_fps:.2f}")
#     print("=" * 60)

#     cap.release()

# if __name__ == "__main__":
#     test_capture_only()


#——————————————————————————————————————————————————————————————————————————
#————————————————————————————————USB（画面）————————————————————————————————
#——————————————————————————————————————————————————————————————————————————

# import cv2
# import time

# def run_camera_test_with_display():
#     # 打开 USB 摄像头 /dev/video1
#     cap = cv2.VideoCapture(1, cv2.CAP_V4L2)

#     if not cap.isOpened():
#         print("[错误] 无法打开摄像头 /dev/video1")
#         return

#     # 强制 MJPG
#     cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

#     # 设置为摄像头支持的模式
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
#     cap.set(cv2.CAP_PROP_FPS, 60)

#     actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     actual_fps = cap.get(cv2.CAP_PROP_FPS)

#     print("=" * 50)
#     print(f"硬件配置结果: {actual_w}x{actual_h} @ {actual_fps:.2f} FPS")
#     print("按 q 退出")
#     print("=" * 50)

#     prev_time = time.time()
#     frame_count = 0

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             print("[错误] 无法获取帧")
#             break

#         frame_count += 1
#         curr_time = time.time()
#         elapsed = curr_time - prev_time

#         if elapsed >= 1.0:
#             fps = frame_count / elapsed
#             print(f"实时帧率: {fps:.1f} FPS")
#             frame_count = 0
#             prev_time = curr_time

#         cv2.imshow("USB Camera Test", frame)

#         key = cv2.waitKey(1) & 0xFF
#         if key == ord('q'):
#             break

#     cap.release()
#     cv2.destroyAllWindows()
#     print("测试结束")
    

# if __name__ == "__main__":
#     run_camera_test_with_display()

#——————————————————————————————————————————————————————————————————————————
#————————————————————————————————CSI（画面）————————————————————————————————
#——————————————————————————————————————————————————————————————————————————

# import time
# import cv2
# from picamera2 import Picamera2

# WIDTH = 640
# HEIGHT = 480
# TARGET_FPS = 60

# picam2 = Picamera2()

# config = picam2.create_video_configuration(
#     main={"size": (WIDTH, HEIGHT), "format": "YUV420"},
#     controls={"FrameRate": TARGET_FPS}
# )

# picam2.configure(config)
# picam2.start()

# time.sleep(2)

# prev_time = time.time()

# print("Start... Press q to quit.")

# try:
#     while True:
#         # 取一帧请求，这样图像和 metadata 是同一帧
#         request = picam2.capture_request()

#         # 当前帧图像
#         yuv = request.make_array("main")

#         # 当前帧 metadata
#         metadata = request.get_metadata()

#         # YUV420 -> BGR，供 OpenCV 显示
#         frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

#         # -------------------------
#         # 1) 相机实时帧率（从 metadata 获取）
#         # -------------------------
#         frame_duration = metadata.get("FrameDuration", None)
#         camera_fps = 0.0
#         if frame_duration and frame_duration > 0:
#             camera_fps = 1000000.0 / frame_duration   # FrameDuration 单位是微秒

#         # -------------------------
#         # 2) 当前程序实际处理帧率（实时）
#         # -------------------------
#         now = time.time()
#         dt = now - prev_time
#         prev_time = now

#         process_fps = 0.0
#         if dt > 0:
#             process_fps = 1.0 / dt

#         # 显示到画面上
#         cv2.putText(
#             frame,
#             f"Camera FPS: {camera_fps:.2f}",
#             (20, 40),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.8,
#             (0, 255, 0),
#             2
#         )

#         cv2.putText(
#             frame,
#             f"Process FPS: {process_fps:.2f}",
#             (20, 80),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.8,
#             (0, 255, 255),
#             2
#         )

#         # 终端也实时打印
#         print(f"\rCamera FPS: {camera_fps:.2f} | Process FPS: {process_fps:.2f}", end="")

#         cv2.imshow("CSI Camera", frame)

#         request.release()

#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

# except KeyboardInterrupt:
#     print("\nStopped.")

# finally:
#     cv2.destroyAllWindows()
#     picam2.stop()


#——————————————————————————————————————————————————————————————————————————
#————————————————————————————————CSI（无画面）————————————————————————————————
#——————————————————————————————————————————————————————————————————————————

# import time
# from picamera2 import Picamera2

# WIDTH = 640
# HEIGHT = 480
# TARGET_FPS = 60

# picam2 = Picamera2()

# config = picam2.create_video_configuration(
#     main={"size": (WIDTH, HEIGHT), "format": "YUV420"},
#     controls={"FrameRate": TARGET_FPS}
# )

# picam2.configure(config)
# picam2.start()

# time.sleep(2)

# print("Start... Press Ctrl+C to quit.")

# # 上一帧的传感器时间戳，用来判断是不是新帧
# last_sensor_ts = None

# # 统计窗口
# window_start = time.time()
# window_count = 0

# # 当前显示值
# camera_fps_display = 0.0
# process_fps_display = 0.0

# try:
#     while True:
#         request = picam2.capture_request()

#         # 取图像（虽然这里不显示，但保持你的流程基本一致）
#         yuv = request.make_array("main")

#         # 取 metadata
#         metadata = request.get_metadata()

#         # -------------------------
#         # 1) 相机实时帧率（直接来自 metadata）
#         # -------------------------
#         frame_duration = metadata.get("FrameDuration", None)
#         if frame_duration and frame_duration > 0:
#             camera_fps_display = 1000000.0 / frame_duration  # 微秒 -> FPS

#         # -------------------------
#         # 2) 真实处理帧率：按“唯一新帧”统计
#         # -------------------------
#         sensor_ts = metadata.get("SensorTimestamp", None)

#         # 只有拿到新帧，才记一次
#         if sensor_ts is not None and sensor_ts != last_sensor_ts:
#             window_count += 1
#             last_sensor_ts = sensor_ts

#         now = time.time()
#         elapsed = now - window_start

#         # 每 0.5 秒更新一次显示，更像实时，又不会乱跳
#         if elapsed >= 0.5:
#             process_fps_display = window_count / elapsed
#             window_count = 0
#             window_start = now

#         print(
#             f"\rCamera FPS: {camera_fps_display:.2f} | Process FPS: {process_fps_display:.2f}",
#             end=""
#         )

#         request.release()

# except KeyboardInterrupt:
#     print("\nStopped.")

# finally:
#     picam2.stop()









# import cv2
# import time

# def main():
#     width, height, fps = 640, 480, 60

#     cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
#     cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
#     cap.set(cv2.CAP_PROP_FPS, fps)

#     if not cap.isOpened():
#         print("open camera failed")
#         return

#     pipeline = (
#         "appsrc ! "
#         "video/x-raw,format=BGR,width=640,height=480,framerate=60/1 ! "
#         "videoconvert ! "
#         "kmssink sync=false"
#     )

#     out = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, 0, fps, (width, height), True)

#     if not out.isOpened():
#         print("open gstreamer output failed")
#         cap.release()
#         return

#     prev = time.time()
#     count = 0
#     start = time.time()

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             print("read failed")
#             break

#         # 这里放你的 OpenCV 处理
#         cv2.putText(frame, "OpenCV -> GStreamer", (20, 40),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

#         out.write(frame)

#         count += 1
#         now = time.time()
#         if now - prev >= 1.0:
#             fps_now = count / (now - start)
#             print(f"\ravg fps = {fps_now:.2f}", end="", flush=True)

#     cap.release()
#     out.release()

# if __name__ == "__main__":
#     main()

# import time
# import numpy as np
# from picamera2 import Picamera2

# def test_picamera2_high_fps():
#     # --- 配置参数 ---
#     width = 1296    
#     height = 972
#     test_fps = 60  # 目标帧率
#     duration = 10  # 测试时长
    
#     picam2 = Picamera2()
    
#     # 1. 创建视频配置
#     config = picam2.create_video_configuration(
#         main={"size": (width, height), "format": "YUV420"}
#     )
#     picam2.configure(config)

#     # 2. 关键控制参数设置
#     # FrameRate: 强制要求硬件输出 60fps
#     # ExposureTime: 固定曝光时间为 15ms，防止自动曝光拉低帧率
#     picam2.set_controls({
#         "FrameRate": test_fps,
#         "ExposureTime": 20000 
#     })

#     picam2.start()

#     # 3. 预热阶段 (Warmup)
#     # 丢弃前 30 帧，确保 ISP 稳定
#     for _ in range(30):
#         picam2.capture_array()

#     print("=" * 60)
#     print(f"开始测试: {width}x{height}, 目标 {test_fps}FPS, YUV420")
#     print("=" * 60)

#     # 4. 主测试循环
#     start_time = time.time()
#     frame_count = 0

#     try:
#         while True:
#             # capture_array 包含硬件捕获 + 内存拷贝到 NumPy 数组的过程
#             frame = picam2.capture_array()
            
#             if frame is None:
#                 print("捕获失败")
#                 break

#             frame_count += 1

#             # 到达设定时长退出
#             if time.time() - start_time >= duration:
#                 break
                
#     except KeyboardInterrupt:
#         print("\n用户中止测试")

#     elapsed = time.time() - start_time
#     actual_fps = frame_count / elapsed if elapsed > 0 else 0.0

#     # 5. 结果输出
#     print("=" * 60)
#     print(f"实际测试时长: {elapsed:.3f} s")
#     print(f"总计捕获帧数: {frame_count}")
#     print(f"最终平均 FPS: {actual_fps:.2f}")
#     print("=" * 60)

#     picam2.stop()

# if __name__ == "__main__":
#     test_picamera2_high_fps()

# import time
# import sys
# import cv2
# import numpy as np
# from picamera2 import Picamera2

# def test_opencv_fast_feedback():
#     width, height = 1296, 972
#     target_fps = 60
    
#     picam2 = Picamera2()
    
#     # 1. 硬件配置
#     config = picam2.create_video_configuration(
#         main={"size": (width, height), "format": "YUV420"}
#     )
#     picam2.configure(config)
#     picam2.set_controls({
#         "FrameRate": target_fps,
#         "ExposureTime": 20000 
#     })

#     picam2.start()

#     print("=" * 60)
#     print(f"模式: {width}x{height} | 正在进行高频采样测试...")
#     print("=" * 60)

#     # 统计变量
#     frame_count = 0
#     start_time = time.time()
#     last_print_time = start_time
#     total_frames = 0
#     spinner = ["|", "/", "-", "\\"] # 旋转小图标
#     spinner_idx = 0

#     try:
#         while True:
#             # --- 核心处理链路 ---
#             frame = picam2.capture_array()
#             if frame is None:
#                 break
            
#             # 颜色转换（3B+ 的主要负担）
#             cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)
            
#             # --- 统计逻辑 ---
#             frame_count += 1
#             total_frames += 1
#             current_time = time.time()
            
#             # 【核心修改】将刷新间隔改为 0.1 秒，反馈速度提升 10 倍
#             delta = current_time - last_print_time
#             if delta >= 0.1:
#                 fps = frame_count / delta
#                 elapsed = current_time - start_time
                
#                 # 构造显示字符串
#                 s = spinner[spinner_idx % 4]
#                 status = f"\r{s} [采样中] 时间:{elapsed:5.1f}s | 瞬时:{fps:5.2f} FPS | 累计:{total_frames:5d}"
                
#                 sys.stdout.write(status)
#                 sys.stdout.flush()
                
#                 # 重置局部计数
#                 frame_count = 0
#                 last_print_time = current_time
#                 spinner_idx += 1

#     except KeyboardInterrupt:
#         print("\n" + "=" * 60)
#         final_elapsed = time.time() - start_time
#         final_fps = total_frames / final_elapsed if final_elapsed > 0 else 0
#         print(f"测试完成! 平均 FPS: {final_fps:.2f}")
#     finally:
#         picam2.stop()

# if __name__ == "__main__":
#     test_opencv_fast_feedback()

# import time
# import sys
# from picamera2 import Picamera2

# def start_hdmi_hardware_preview():
#     # 1. 初始化
#     picam2 = Picamera2()

#     # 2. 配置黄金模式：1296x972 (OV5647 的 46FPS 极限模式)
#     config = picam2.create_video_configuration(
#         main={"size": (640, 480), "format": "YUV420"}
#     )
#     picam2.configure(config)

#     # 3. 锁定高性能控制参数
#     picam2.set_controls({
#         "FrameRate": 60,       # 强制硬件高帧率
#         "ExposureTime": 20000, # 20ms 曝光，兼顾画面亮度和帧率
#         "Saturation": 1.1,      # 画面鲜艳度
#         "Sharpness": 1.5        # 增加锐度，让大屏幕显示更清晰
#     })

#     print("=" * 60)
#     print("正在启动 [HDMI 硬件层叠] 预览...")
#     print("模式：KMS/DRM Zero-Copy (不占用 CPU)")
#     print("提示：画面将直接覆盖在终端上方，按 Ctrl+C 退出")
#     print("=" * 60)

#     # 4. 启动硬件预览
#     # 在纯终端下，这个方法会直接调用 DRM 驱动将图像渲染到 HDMI 物理层
#     picam2.start_preview()
#     picam2.start()

#     # 5. 性能监控循环
#     frame_count = 0
#     start_time = time.time()
#     last_print_time = start_time
#     total_frames = 0

#     try:
#         while True:
#             # 这里我们仍然调用 capture_array() 是为了在终端打印 FPS
#             # 如果你纯粹只想看画面，甚至不需要下面这行，CPU 占用将几乎为 0
#             picam2.capture_array()
            
#             frame_count += 1
#             total_frames += 1
#             current_time = time.time()
            
#             # 每 0.1 秒刷新一次终端状态
#             delta = current_time - last_print_time
#             if delta >= 0.1:
#                 fps = frame_count / delta
#                 elapsed = current_time - start_time
#                 sys.stdout.write(f"\r[监控中] 时间:{elapsed:5.1f}s | 瞬时:{fps:5.2f} FPS | 累计:{total_frames:5d} 帧")
#                 sys.stdout.flush()
                
#                 frame_count = 0
#                 last_print_time = current_time

#     except KeyboardInterrupt:
#         print("\n" + "=" * 60)
#         print("停止预览并释放硬件资源。")
#     finally:
#         picam2.stop_preview()
#         picam2.stop()

# if __name__ == "__main__":
#     start_hdmi_hardware_preview()

# import time
# import sys
# from picamera2 import Picamera2

# try:
#     try:
#         from picamera2.preview import DrmPreview
#     except ImportError:
#         from picamera2.previews import DrmPreview
# except ImportError:
#     print("未找到 picamera2 预览模块")
#     sys.exit(1)

# class SimpleCounter:
#     def __init__(self):
#         self.count = 0

#     def increment(self, request):
#         self.count += 1

# def run_performance_test():
#     picam2 = Picamera2()
#     counter = SimpleCounter()

#     config = picam2.create_video_configuration(
#         main={"size": (1296, 972), "format": "YUV420"}
#     )
#     picam2.configure(config)

#     # 关键修改：不要用 request_completed
#     picam2.post_callback = counter.increment

#     picam2.set_controls({
#         "FrameRate": 60,
#         "ExposureTime": 15000,
#         "AeEnable": True
#     })

#     print("-" * 60)
#     print("【系统状态】正在启动硬件加速预览...")
#     print("【系统状态】如果看到这行字，说明终端是活的")
#     print("-" * 60)

#     picam2.start_preview(DrmPreview())
#     picam2.start()

#     last_time = time.time()
#     start_time = time.time()
#     last_frame_count = 0

#     try:
#         while True:
#             time.sleep(1)

#             now = time.time()
#             duration = now - last_time
#             current_total_frames = counter.count

#             frames_this_second = current_total_frames - last_frame_count
#             fps = frames_this_second / duration if duration > 0 else 0

#             print(
#                 f">>> [监控] 实时帧率: {fps:.2f} FPS | 总捕获帧数: {current_total_frames} | 运行时间: {int(now - start_time)}s",
#                 flush=True
#             )

#             last_frame_count = current_total_frames
#             last_time = now

#     except KeyboardInterrupt:
#         print("\n正在安全关闭...")
#     finally:
#         picam2.stop()

# if __name__ == "__main__":
#     run_performance_test()

# import time
# import sys
# import cv2  # 导入 OpenCV
# import numpy as np
# from picamera2 import Picamera2

# try:
#     try:
#         from picamera2.preview import DrmPreview
#     except ImportError:
#         from picamera2.previews import DrmPreview
# except ImportError:
#     print("未找到 picamera2 预览模块")
#     sys.exit(1)

# class OpenCVProcessor:
#     def __init__(self):
#         self.count = 0
#         self.last_frame = None

#     def process_frame(self, request):
#         # 1. 从 request 中提取 NumPy 数组 (YUV420 格式)
#         # "main" 对应后面 configuration 中的流名称
#         yuv_data = request.make_array("main")

#         # 2. (可选) 转换为 BGR 格式以便 OpenCV 处理
#         # 注意：YUV420 转换 BGR 会消耗一定 CPU，如果只求计帧可以跳过此步
#         # frame_bgr = cv2.cvtColor(yuv_data, cv2.COLOR_YUV2BGR_I420)

#         # 3. 在这里放置你的 OpenCV 算法逻辑
#         # 例如：gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
#         # 计数
#         self.count += 1
#         # self.last_frame = frame_bgr # 如果主循环需要访问最后一帧

# def run_performance_test():
#     picam2 = Picamera2()
#     processor = OpenCVProcessor()

#     # 配置流：确保 main 流的格式与 make_array 匹配
#     config = picam2.create_video_configuration(
#         main={"size": (1296, 972), "format": "YUV420"}
#     )
#     picam2.configure(config)

#     # 关键点：将回调指向 OpenCV 处理函数
#     picam2.post_callback = processor.process_frame

#     picam2.set_controls({
#         "FrameRate": 60,
#         "ExposureTime": 15000,
#         "AeEnable": True
#     })

#     print("-" * 60)
#     print("【模式】OpenCV 环境测试 (DRM 硬件显示)")
#     print("【状态】正在启动...")
#     print("-" * 60)

#     # 保持 DRM 预览，实现丝滑显示
#     picam2.start_preview(DrmPreview())
#     picam2.start()

#     last_time = time.time()
#     start_time = time.time()
#     last_frame_count = 0

#     try:
#         while True:
#             time.sleep(1)

#             now = time.time()
#             duration = now - last_time
#             current_total_frames = processor.count

#             fps = (current_total_frames - last_frame_count) / duration if duration > 0 else 0

#             print(
#                 f">>> [监控] 处理帧率: {fps:.2f} FPS | 已处理总数: {current_total_frames} | 运行时间: {int(now - start_time)}s",
#                 flush=True
#             )

#             last_frame_count = current_total_frames
#             last_time = now

#     except KeyboardInterrupt:
#         print("\n正在安全关闭...")
#     finally:
#         picam2.stop()

# if __name__ == "__main__":
#     run_performance_test()

import time
import sys
import cv2
import threading
from picamera2 import Picamera2

try:
    try:
        from picamera2.preview import DrmPreview
    except ImportError:
        from picamera2.previews import DrmPreview
except ImportError:
    print("未找到 picamera2 预览模块")
    sys.exit(1)


# =========================================================
# 配置区
# =========================================================

# 分辨率：建议先用 640x480 做基线，后续再测更高分辨率
FRAME_SIZE = (640, 480)

# 请求帧率（实际是否达到取决于 sensor mode / 曝光 / ISP / CPU）
TARGET_FPS = 60

# 是否启用一个“极轻量”的 OpenCV 操作，帮助验证不是只靠 YUV->BGR 才高 FPS
# False: 只测 YUV->BGR 基础链路
# True : 额外做一次 BGR->GRAY
ENABLE_LIGHT_OPENCV_STEP = False

# 是否启用 DRM 预览
ENABLE_PREVIEW = True

# 每隔多少秒打印一次统计
PRINT_INTERVAL = 1.0


class OpenCVProcessor:
    def __init__(self):
        self.total_count = 0
        self.total_process_time_ms = 0.0

        self.period_count = 0
        self.period_process_time_ms = 0.0

        self.last_frame_bgr = None
        self.lock = threading.Lock()

    def process_frame(self, request):
        start_proc = time.perf_counter()

        # 1. 取出 YUV420 数据
        yuv_data = request.make_array("main")

        # 2. 转成 OpenCV 常用 BGR
        frame_bgr = cv2.cvtColor(yuv_data, cv2.COLOR_YUV2BGR_I420)

        # ---------------------------------------------------------
        # 【基线链路结束 / 应用层入口开始】
        # 在这里逐步加入你后续真正的应用层代码
        # ---------------------------------------------------------

        if ENABLE_LIGHT_OPENCV_STEP:
            # 轻量操作示例：转灰度
            _gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # 保存最后一帧引用，仅用于调试观察
        self.last_frame_bgr = frame_bgr

        # ---------------------------------------------------------
        # 【应用层入口结束】
        # ---------------------------------------------------------

        elapsed_ms = (time.perf_counter() - start_proc) * 1000.0

        with self.lock:
            self.total_count += 1
            self.total_process_time_ms += elapsed_ms

            self.period_count += 1
            self.period_process_time_ms += elapsed_ms

    def snapshot_and_reset_period(self):
        with self.lock:
            result = {
                "period_count": self.period_count,
                "period_process_time_ms": self.period_process_time_ms,
                "total_count": self.total_count,
                "total_process_time_ms": self.total_process_time_ms,
            }
            self.period_count = 0
            self.period_process_time_ms = 0.0
            return result


def run_performance_test():
    picam2 = Picamera2()
    processor = OpenCVProcessor()

    # 配置视频流
    config = picam2.create_video_configuration(
        main={"size": FRAME_SIZE, "format": "YUV420"}
    )
    picam2.configure(config)

    # 注册后处理回调
    picam2.post_callback = processor.process_frame

    # 尝试设置高帧率
    # 注意：实际帧率会受到 sensor mode / 自动曝光 / 光照条件影响
    picam2.set_controls({
        "FrameRate": TARGET_FPS,
        "ExposureTime": 15000,
        "AeEnable": True
    })

    print("-" * 70)
    print("【模式】OpenCV 基线性能测试 (包含 YUV420 -> BGR)")
    print(f"【分辨率】{FRAME_SIZE[0]} x {FRAME_SIZE[1]}")
    print(f"【目标帧率】{TARGET_FPS} FPS")
    print(f"【轻量OpenCV步骤】{'开启(BGR->GRAY)' if ENABLE_LIGHT_OPENCV_STEP else '关闭'}")
    print("【说明】终端中的 [处理帧率] 才是你要关注的核心指标")
    print("-" * 70)

    # 启动
    if ENABLE_PREVIEW:
        picam2.start_preview(DrmPreview())
    picam2.start()

    test_start_time = time.time()
    last_print_time = test_start_time

    try:
        while True:
            time.sleep(PRINT_INTERVAL)

            now = time.time()
            duration = now - last_print_time
            stats = processor.snapshot_and_reset_period()

            period_count = stats["period_count"]
            period_process_time_ms = stats["period_process_time_ms"]
            total_count = stats["total_count"]
            total_process_time_ms = stats["total_process_time_ms"]

            # 区间处理帧率
            fps = period_count / duration if duration > 0 else 0.0

            # 这一统计区间内的平均单帧处理耗时
            avg_ms_period = (
                period_process_time_ms / period_count if period_count > 0 else 0.0
            )

            # 累计平均单帧处理耗时
            avg_ms_total = (
                total_process_time_ms / total_count if total_count > 0 else 0.0
            )

            elapsed_total = now - test_start_time

            print(
                f">>> [监控] 区间处理帧率: {fps:6.2f} FPS | "
                f"区间平均耗时: {avg_ms_period:6.2f} ms | "
                f"累计平均耗时: {avg_ms_total:6.2f} ms | "
                f"已处理总数: {total_count:8d} | "
                f"运行时长: {elapsed_total:7.1f} s",
                flush=True
            )

            last_print_time = now

    except KeyboardInterrupt:
        print("\n正在安全关闭...")

    finally:
        picam2.stop()


if __name__ == "__main__":
    run_performance_test()

