import cv2 as cv
from picamera2 import MappedArray, Picamera2

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
        self.callback = None

    def open(
        self,
        main_size=(640, 480),
        fps=60,
        enable_preview=True,
        use_manual_camera=False,
        manual_exposure_us=None,
        manual_analog_gain=None,
        frame_duration_us=None,
    ):
        if self.is_opened:
            return True

        try:
            self.main_size = main_size
            self.picam2 = Picamera2()
            config = self.picam2.create_video_configuration(
                main={"size": self.main_size, "format": "BGR888"}
            )
            self.picam2.configure(config)

            controls = {}
            if use_manual_camera:
                if frame_duration_us is not None:
                    controls["FrameDurationLimits"] = (frame_duration_us, frame_duration_us)
                controls["AeEnable"] = False
                if manual_exposure_us is not None:
                    controls["ExposureTime"] = manual_exposure_us
                if manual_analog_gain is not None:
                    controls["AnalogueGain"] = manual_analog_gain
            else:
                controls["FrameRate"] = fps
                controls["AeEnable"] = True

            if controls:
                self.picam2.set_controls(controls)

            if enable_preview and DrmPreview is not None:
                self.picam2.start_preview(DrmPreview())

            if self.callback is not None:
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
        self.callback = callback_func
        if self.is_opened and self.picam2 is not None:
            self.picam2.post_callback = self._internal_callback

    def _internal_callback(self, request):
        if self.callback is None:
            return

        with MappedArray(request, "main") as mapped:
            frame_bgr = mapped.array.copy()
        self.callback(frame_bgr)

    def capture_bgr(self):
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
