"""
模块名称：camera.py
功能说明：封装 Picamera2 相机初始化、3A/手动曝光控制、预览显示与帧回调接口
输入：CameraConfig 配置对象、上层注册的帧回调函数
输出：BGR 图像帧、同步抓帧结果
依赖项：picamera2、libcamera、cv2
"""

from dataclasses import dataclass
from typing import Optional

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


@dataclass(slots=True)
class CameraConfig:
    main_size: tuple[int, int] = (640, 480)
    fps: int = 60

    enable_preview: bool = True
    preview_fullscreen: bool = True
    preview_x: int = 0
    preview_y: int = 0
    preview_width: Optional[int] = None
    preview_height: Optional[int] = None

    use_manual_camera: bool = False
    manual_exposure_us: Optional[int] = None
    manual_analog_gain: Optional[float] = None
    frame_duration_us: Optional[int] = None

    enable_3a: bool = True
    enable_awb: bool = True
    enable_af: bool = False
    af_mode: str = "continuous"


class Camera:
    def __init__(self, config: Optional[CameraConfig] = None):
        self.picam2 = None
        self.is_opened = False
        self.config = config or CameraConfig()
        self.main_size = self.config.main_size
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

    def _build_controls(self, config: CameraConfig):
        controls = {}
        if config.use_manual_camera:
            # 比赛或固定光照场景下，用手动曝光把相机“锁死”。
            # 这样可以显著减少自动曝光导致的亮度跳变，
            # 对后面的 Otsu 阈值分割和黑框黑度判断更友好。
            if config.frame_duration_us is not None:
                controls["FrameDurationLimits"] = (
                    config.frame_duration_us,
                    config.frame_duration_us,
                )
            controls["AeEnable"] = False
            if config.manual_exposure_us is not None:
                controls["ExposureTime"] = config.manual_exposure_us
            if config.manual_analog_gain is not None:
                controls["AnalogueGain"] = config.manual_analog_gain
            return controls

        # 3A 属于 libcamera/ISP 管线的一部分，处理结果会直接体现在
        # 后面拿到的主图像流里，所以显示和识别看到的是同一套自动调节结果。
        controls["FrameRate"] = config.fps
        controls["AeEnable"] = bool(config.enable_3a)
        controls["AwbEnable"] = bool(config.enable_3a and config.enable_awb)

        if config.enable_3a and config.enable_af:
            resolved_af_mode = self._resolve_af_mode(config.af_mode)
            if resolved_af_mode is not None:
                controls["AfMode"] = resolved_af_mode
        return controls

    def _start_preview(self, config: CameraConfig):
        if not config.enable_preview or DrmPreview is None:
            return

        # DRM 预览是直接走显示硬件的，不经过 OpenCV 窗口。
        # 它的作用主要是“看画面是否正常”，而不是给识别线程供图。
        # 所以开预览不会改变识别输入，只是增加一个底层显示通路。
        drm_width = config.preview_width
        drm_height = config.preview_height
        if config.preview_fullscreen and (drm_width is None or drm_height is None):
            detected_width, detected_height = self._detect_drm_preview_size()
            drm_width = detected_width or config.main_size[0]
            drm_height = detected_height or config.main_size[1]
        elif drm_width is None or drm_height is None:
            drm_width = config.main_size[0]
            drm_height = config.main_size[1]

        self.picam2.start_preview(
            DrmPreview(
                x=config.preview_x,
                y=config.preview_y,
                width=drm_width,
                height=drm_height,
            )
        )

    def open(self, config: Optional[CameraConfig] = None):
        if self.is_opened:
            return True

        try:
            if config is not None:
                self.config = config

            self.main_size = self.config.main_size
            self.picam2 = Picamera2()
            # 这里让 Picamera2 直接输出 BGR888。
            # 这样 BlackSearch 收到的就是 OpenCV 可直接处理的格式，
            # 不需要再走一次 YUV/RGB 转换，识别链路更简单也更稳定。
            config = self.picam2.create_video_configuration(
                main={"size": self.main_size, "format": "BGR888"}
            )
            self.picam2.configure(config)

            self._apply_controls(self._build_controls(self.config))
            self._start_preview(self.config)

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
