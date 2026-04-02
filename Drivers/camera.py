import cv2 as cv
import re
import subprocess
from picamera2 import MappedArray, Picamera2
from libcamera import controls as libcamera_controls

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
        # 上层把识别函数挂到这里；每来一帧就会走一次回调。
        self.callback = None

    def _resolve_af_mode(self, af_mode):
        if af_mode is None:
            return None

        af_mode_map = {
            "manual": libcamera_controls.AfModeEnum.Manual,
            "auto": libcamera_controls.AfModeEnum.Auto,
            "continuous": libcamera_controls.AfModeEnum.Continuous,
        }
        return af_mode_map.get(str(af_mode).strip().lower())

    def _apply_controls(self, controls):
        if not controls:
            return

        try:
            self.picam2.set_controls(controls)
        except Exception as exc:
            # 很多模组并不支持 AF。遇到这类能力不支持时，退化到 AE/AWB 继续运行。
            if "AfMode" in controls:
                fallback_controls = dict(controls)
                fallback_controls.pop("AfMode", None)
                self.picam2.set_controls(fallback_controls)
                print(f"AF 控制不可用，已退化为 AE/AWB: {exc}")
                return
            raise

    def _detect_drm_preview_size(self):
        try:
            result = subprocess.run(
                ["kmsprint"],
                check=True,
                capture_output=True,
                text=True,
            )
            match = re.search(r"Crtc\s+\d+\s+\(\d+\)\s+(\d+)x(\d+)@", result.stdout)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return None, None

    def open(
        self,
        main_size=(640, 480),
        fps=60,
        enable_preview=True,
        use_manual_camera=False,
        manual_exposure_us=None,
        manual_analog_gain=None,
        frame_duration_us=None,
        enable_3a=True,
        enable_awb=True,
        enable_af=False,
        af_mode="continuous",
        preview_fullscreen=True,
        preview_x=0,
        preview_y=0,
        preview_width=None,
        preview_height=None,
    ):
        if self.is_opened:
            return True

        try:
            self.main_size = main_size
            self.picam2 = Picamera2()
            # 这里让 Picamera2 直接输出 BGR888。
            # 这样 BlackSearch 收到的就是 OpenCV 可直接处理的格式，
            # 不需要再走一次 YUV/RGB 转换，识别链路更简单也更稳定。
            config = self.picam2.create_video_configuration(
                main={"size": self.main_size, "format": "BGR888"}
            )
            self.picam2.configure(config)

            controls = {}
            if use_manual_camera:
                # 比赛或固定光照场景下，用手动曝光把相机“锁死”。
                # 这样可以显著减少自动曝光导致的亮度跳变，
                # 对后面的 Otsu 阈值分割和黑框黑度判断更友好。
                if frame_duration_us is not None:
                    controls["FrameDurationLimits"] = (frame_duration_us, frame_duration_us)
                controls["AeEnable"] = False
                if manual_exposure_us is not None:
                    controls["ExposureTime"] = manual_exposure_us
                if manual_analog_gain is not None:
                    controls["AnalogueGain"] = manual_analog_gain
            else:
                # 3A 属于 libcamera/ISP 管线的一部分，处理结果会直接体现在
                # 后面拿到的主图像流里，所以显示和识别看到的是同一套自动调节结果。
                controls["FrameRate"] = fps
                controls["AeEnable"] = bool(enable_3a)
                controls["AwbEnable"] = bool(enable_3a and enable_awb)

                if enable_3a and enable_af:
                    resolved_af_mode = self._resolve_af_mode(af_mode)
                    if resolved_af_mode is not None:
                        controls["AfMode"] = resolved_af_mode

            self._apply_controls(controls)

            if enable_preview and DrmPreview is not None:
                # DRM 预览是直接走显示硬件的，不经过 OpenCV 窗口。
                # 它的作用主要是“看画面是否正常”，而不是给识别线程供图。
                # 所以开预览不会改变识别输入，只是增加一个底层显示通路。
                drm_width = preview_width
                drm_height = preview_height
                if preview_fullscreen and (drm_width is None or drm_height is None):
                    detected_width, detected_height = self._detect_drm_preview_size()
                    drm_width = detected_width or main_size[0]
                    drm_height = detected_height or main_size[1]
                elif drm_width is None or drm_height is None:
                    drm_width = main_size[0]
                    drm_height = main_size[1]

                self.picam2.start_preview(
                    DrmPreview(
                        x=preview_x,
                        y=preview_y,
                        width=drm_width,
                        height=drm_height,
                    )
                )

            if self.callback is not None:
                # post_callback 由 Picamera2 在底层取到新帧后触发。
                # 我们把它挂在这里，识别线程就能持续收到最新画面。
                self.picam2.post_callback = self._internal_callback

            self.picam2.start()
            self.is_opened = True
            return True
        except Exception as exc:
            print(f"Camera Open Failed: {exc}")
            self.is_opened = False
            self.picam2 = None
            return False

    def set_callback(self, callback_func):
        # 允许先注册识别回调、后开相机，也允许开机后动态替换回调。
        self.callback = callback_func
        if self.is_opened and self.picam2 is not None:
            self.picam2.post_callback = self._internal_callback

    def _internal_callback(self, request):
        if self.callback is None:
            return

        # request 对应的是 Picamera2 当前这帧的底层缓冲区。
        # 这里必须 copy，一旦底层缓冲被下一帧复用，上层识别看到的数据就会乱。
        with MappedArray(request, "main") as mapped:
            frame_bgr = mapped.array.copy()
        self.callback(frame_bgr)

    def capture_bgr(self):
        # 这个接口保留给同步抓拍/调试场景。
        # BlackSearch 主流程走的是回调 + 队列，不依赖这里。
        if not self.is_opened or self.picam2 is None:
            return None
        frame_bgr = self.picam2.capture_array()
        if frame_bgr is None:
            return None
        if frame_bgr.ndim == 3:
            return frame_bgr
        return cv.cvtColor(frame_bgr, cv.COLOR_YUV420p2BGR)

    def close(self):
        if self.is_opened and self.picam2 is not None:
            try:
                self.picam2.stop()
            except Exception:
                pass
        self.is_opened = False
        self.picam2 = None

    def __del__(self):
        self.close()
