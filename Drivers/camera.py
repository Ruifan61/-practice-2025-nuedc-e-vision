# import cv2 as cv

# class Camera:
#     def __init__(self):
#         # 移除 Picamera2 支持，改为 OpenCV 的 VideoCapture
#         self.cvcap = None
#         self.is_opened = False

#     def open(self, main_size=(640, 360)):
#         # 如果摄像头已经打开，则直接返回True
#         if self.is_opened: return True

#         try:
#             # 0 代表默认的第一个 USB 摄像头
#             self.cvcap = cv.VideoCapture(0, cv.CAP_V4L2)
            
#             if not self.cvcap.isOpened():
#                 print("Camera Open Failed: Cannot open USB camera (ID 0)")
#                 self.is_opened = False
#                 return False

#             # 配置摄像头分辨率
#             self.cvcap.set(cv.CAP_PROP_FRAME_WIDTH, main_size[0])
#             self.cvcap.set(cv.CAP_PROP_FRAME_HEIGHT, main_size[1])
#             # USB摄像头一般最大支持30帧或60帧
#             self.cvcap.set(cv.CAP_PROP_FPS, 60)

#             # 设置摄像头已打开标志
#             self.is_opened = True
#             return True

#         except Exception as e:
#             # 打印摄像头打开失败的错误信息
#             print(f"Camera Open Failed: {str(e)}")
#             # 设置摄像头未打开标志
#             self.is_opened = False
#             return False

#     def capture(self, resize=None):
#         # 如果摄像头未打开，则返回None
#         if not self.is_opened: return None

#         try:
#             # 使用 OpenCV 读取画面
#             ret, frame = self.cvcap.read()
            
#             if not ret or frame is None:
#                 return None

#             # OpenCV 读取的画面默认就是 BGR 格式，不需要像 Picamera 那样做 RGBA2BGR 的转换

#             # 【注意】这里保留了您原代码的旋转180度逻辑。
#             # 如果您发现画面是倒过来的，请把下面这行前面加个 # 注释掉
#             frame = cv.rotate(frame, cv.ROTATE_180)

#             # 调整大小（如BlackSearch中使用的640x480）
#             if resize and isinstance(resize, tuple) and len(resize) == 2:
#                 frame = cv.resize(frame, resize)
                
#             # 返回捕获到的图像
#             return frame
            
#         # 捕获异常并打印错误信息
#         except Exception as e:
#             print(f"Image Capture Failed: {str(e)}")
#             # 返回None
#             return None

#     def close(self):
#         if self.is_opened and self.cvcap is not None:
#             self.cvcap.release()
#             self.is_opened = False

#     def __del__(self):
#         # 确保对象销毁时释放资源
#         self.close()

# import cv2 as cv
# from picamera2 import Picamera2


# class Camera:
#     def __init__(self):
#         self.picam2 = None
#         self.is_opened = False
#         self.main_size = (640, 360)

#     def open(self, main_size=(640, 360), lores_size=None, fps=60):
#         # 如果摄像头已经打开，则直接返回 True
#         if self.is_opened:
#             return True

#         try:
#             self.main_size = main_size
#             self.picam2 = Picamera2()

#             # 创建视频配置
#             config = self.picam2.create_video_configuration(
#                 main={"size": main_size, "format": "BGR888"},
#                 lores={"size": lores_size} if lores_size else None,
#                 display="main",
#                 controls={"FrameRate": fps}
#             )

#             self.picam2.configure(config)
#             self.picam2.start()

#             self.is_opened = True
#             return True

#         except Exception as e:
#             print(f"Camera Open Failed: {str(e)}")
#             self.is_opened = False
#             self.picam2 = None
#             return False

#     def capture(self, resize=None, rotate_180=False):
#         # 如果摄像头未打开，则返回 None
#         if not self.is_opened or self.picam2 is None:
#             return None

#         try:
#             # Picamera2 在 main format=BGR888 时，capture_array() 可直接给 OpenCV 用
#             frame = self.picam2.capture_array()

#             if frame is None:
#                 return None

#             # 如果画面倒置，可开启 180 度旋转
#             if rotate_180:
#                 frame = cv.rotate(frame, cv.ROTATE_180)

#             # 调整大小
#             if resize and isinstance(resize, tuple) and len(resize) == 2:
#                 frame = cv.resize(frame, resize)

#             return frame

#         except Exception as e:
#             print(f"Image Capture Failed: {str(e)}")
#             return None

#     def close(self):
#         if self.is_opened and self.picam2 is not None:
#             try:
#                 self.picam2.stop()
#             except Exception:
#                 pass

#             self.picam2 = None
#             self.is_opened = False

#     def __del__(self):
#         self.close()


import cv2 as cv
import numpy as np
import time
from picamera2 import Picamera2

try:
    try:
        from picamera2.preview import DrmPreview
    except ImportError:
        from picamera2.previews import DrmPreview
except ImportError:
    DrmPreview = None

class Camera:
    def __init__(self):
        self.picam2 = None
        self.is_opened = False
        self.main_size = (640, 480)
        self.callback = None  # 外部处理逻辑的回调

    def open(self, main_size=(640, 480), fps=60, enable_preview=True):
        """
        打开摄像头并配置高性能模式
        :param enable_preview: 是否开启硬件 DRM 预览（不占 CPU，直通 HDMI）
        """
        if self.is_opened:
            return True

        try:
            self.main_size = main_size
            self.picam2 = Picamera2()

            # 1. 采用 YUV420 格式以获得极致性能
            config = self.picam2.create_video_configuration(
                main={"size": self.main_size, "format": "YUV420"}
            )
            self.picam2.configure(config)

            # 2. 硬件参数设置
            self.picam2.set_controls({
                "FrameRate": fps,
                "AeEnable": True
            })

            # 3. 硬件 DRM 预览启动
            if enable_preview and DrmPreview:
                self.picam2.start_preview(DrmPreview())

            # 4. 启动相机
            self.picam2.start()
            self.is_opened = True
            return True

        except Exception as e:
            print(f"Camera Open Failed: {str(e)}")
            self.is_opened = False
            return False

    def set_callback(self, callback_func):
        """
        设置帧处理回调。
        回调函数应接受两个参数: (request, yuv_array)
        """
        self.callback = callback_func
        if self.is_opened:
            self.picam2.post_callback = self._internal_callback

    def _internal_callback(self, request):
        """
        Picamera2 内部线程调用的原始回调
        """
        if self.callback:
            # 提取 YUV 数据并传给外部处理器
            yuv_array = request.make_array("main")
            self.callback(request, yuv_array)

    def capture_bgr(self):
        """
        传统同步获取 BGR 帧（仅用于简单测试，60FPS 下不建议频繁调用）
        """
        if not self.is_opened: return None
        yuv_data = self.picam2.capture_array()
        if yuv_data is None: return None
        return cv.cvtColor(yuv_data, cv.COLOR_YUV420p2BGR)

    def close(self):
        if self.is_opened and self.picam2 is not None:
            try:
                self.picam2.stop()
            except:
                pass
            self.is_opened = False
            self.picam2 = None

    def __del__(self):
        self.close()