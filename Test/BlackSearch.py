import datetime
import math
import os
import queue
import sys
import threading
import time

import cv2
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from Drivers.camera import Camera


FRAME_SIZE = (1296, 972)
TARGET_FPS = 60

USE_MANUAL_CAMERA = True
MANUAL_EXPOSURE_US = 4000
MANUAL_ANALOG_GAIN = 8.0
FRAME_DURATION_US = int(1_000_000 / TARGET_FPS)

DETECT_SCALE = 4
USE_TRACKING_ROI = True
ROI_HALF_SIZE = 120
MAX_LOST_FRAMES = 5
TRACK_DIST_WEIGHT = 0.8
FULL_FRAME_RESCAN_INTERVAL = 48

MIN_OUTER_AREA = 250
MAX_OUTER_AREA = 50000
MIN_SIDE = 12
MAX_ASPECT_RATIO = 3.6
OUTER_FILL_RATIO_MIN = 0.42
HOLE_RATIO_MIN = 0.12
HOLE_RATIO_MAX = 0.85
CENTER_BLACK_PATCH = 5
CENTER_BLACK_MEAN_MAX = 60
APPROX_EPSILON_FACTOR = 0.03
MIN_APPROX_VERTICES = 4
MAX_APPROX_VERTICES = 12


def get_largest_child_index(contours, hierarchy, parent_idx):
    first_child = hierarchy[0][parent_idx][2]
    if first_child == -1:
        return -1, 0.0

    best_idx = -1
    best_area = 0.0
    child = first_child
    while child != -1:
        area = abs(cv2.contourArea(contours[child]))
        if area > best_area:
            best_area = area
            best_idx = child
        child = hierarchy[0][child][0]
    return best_idx, best_area


def get_center_black_mean(mask, cx, cy, patch_size):
    half = max(1, patch_size // 2)
    y0 = max(0, cy - half)
    y1 = min(mask.shape[0], cy + half + 1)
    x0 = max(0, cx - half)
    x1 = min(mask.shape[1], cx + half + 1)
    if x1 <= x0 or y1 <= y0:
        return 255.0
    return float(np.mean(mask[y0:y1, x0:x1]))


class UltimateHighSpeedTracker:
    def __init__(self):
        self.camera = Camera()
        self.last_center = None
        self.velocity = (0, 0)
        self.lost_count = 0
        self.frame_idx = 0
        self.is_running = True
        self.frame_queue = queue.Queue(maxsize=1)

        self.fps_start_time = time.perf_counter()
        self.fps_frame_count = 0
        self.current_fps = 0.0

    def _callback(self, bgr_array):
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        try:
            self.frame_queue.put_nowait(bgr_array)
        except queue.Full:
            pass

    def _build_search_frame(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        search_frame = frame_bgr
        offset_x = 0
        offset_y = 0

        use_roi = (
            USE_TRACKING_ROI
            and self.last_center is not None
            and self.lost_count <= 2
            and self.frame_idx % FULL_FRAME_RESCAN_INTERVAL != 0
        )
        if not use_roi:
            return search_frame, offset_x, offset_y

        px = self.last_center[0] + self.velocity[0]
        py = self.last_center[1] + self.velocity[1]
        x0 = max(0, int(px - ROI_HALF_SIZE))
        y0 = max(0, int(py - ROI_HALF_SIZE))
        x1 = min(w, int(px + ROI_HALF_SIZE))
        y1 = min(h, int(py + ROI_HALF_SIZE))
        if x1 - x0 <= 20 or y1 - y0 <= 20:
            return search_frame, offset_x, offset_y

        return frame_bgr[y0:y1, x0:x1], x0, y0

    def _detect_target(self, frame_bgr):
        search_frame, offset_x, offset_y = self._build_search_frame(frame_bgr)

        scale = DETECT_SCALE
        small_w = max(1, search_frame.shape[1] // scale)
        small_h = max(1, search_frame.shape[0] // scale)
        small = cv2.resize(search_frame, (small_w, small_h))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        blackhat_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, blackhat_kernel)
        _, mask = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            return None

        best_center = None
        best_score = -1e12
        min_area = MIN_OUTER_AREA / (scale ** 2)
        max_area = MAX_OUTER_AREA / (scale ** 2)

        for index, contour in enumerate(contours):
            outer_area = abs(cv2.contourArea(contour))
            if not (min_area < outer_area < max_area):
                continue

            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, APPROX_EPSILON_FACTOR * perimeter, True)
            if not (MIN_APPROX_VERTICES <= len(approx) <= MAX_APPROX_VERTICES):
                continue

            rect = cv2.minAreaRect(contour)
            (cx, cy), (rw, rh), _ = rect
            if rw < (MIN_SIDE / scale) or rh < (MIN_SIDE / scale):
                continue

            aspect_ratio = max(rw, rh) / max(1.0, min(rw, rh))
            if aspect_ratio > MAX_ASPECT_RATIO:
                continue

            rect_area = rw * rh
            if rect_area <= 0:
                continue
            if (outer_area / rect_area) < OUTER_FILL_RATIO_MIN:
                continue

            child_idx, hole_area = get_largest_child_index(contours, hierarchy, index)
            if child_idx == -1:
                continue

            hole_ratio = hole_area / outer_area
            if not (HOLE_RATIO_MIN < hole_ratio < HOLE_RATIO_MAX):
                continue

            if get_center_black_mean(mask, int(cx), int(cy), CENTER_BLACK_PATCH) > CENTER_BLACK_MEAN_MAX:
                continue

            global_cx = (cx * scale) + offset_x
            global_cy = (cy * scale) + offset_y
            score = outer_area
            if self.last_center is not None:
                dist = math.hypot(global_cx - self.last_center[0], global_cy - self.last_center[1])
                score -= dist * TRACK_DIST_WEIGHT

            if score > best_score:
                best_score = score
                best_center = (int(global_cx), int(global_cy))

        return best_center

    def _log_target(self, center, cost_ms):
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(
            f"[{now}] [TARGET] X:{center[0]:3d} Y:{center[1]:3d} | "
            f"耗时:{cost_ms:3.0f}ms | 帧率: {self.current_fps:4.1f} FPS"
        )

    def _log_predict(self, center):
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(
            f"[{now}] [PREDICT] X:{center[0]:3d} Y:{center[1]:3d} | "
            f"帧率: {self.current_fps:4.1f} FPS"
        )

    def _log_lost(self):
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{now}] [LOST] 等待目标... | 帧率: {self.current_fps:4.1f} FPS")

    def _process_loop(self):
        while self.is_running:
            try:
                frame_bgr = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            now = time.perf_counter()
            self.fps_frame_count += 1
            elapsed = now - self.fps_start_time
            if elapsed >= 1.0:
                self.current_fps = self.fps_frame_count / elapsed
                self.fps_frame_count = 0
                self.fps_start_time = now

            self.frame_idx += 1
            start_time = time.perf_counter()
            best_center = self._detect_target(frame_bgr)

            if best_center is not None:
                if self.last_center is not None:
                    self.velocity = (
                        best_center[0] - self.last_center[0],
                        best_center[1] - self.last_center[1],
                    )
                self.last_center = best_center
                self.lost_count = 0
                cost_ms = (time.perf_counter() - start_time) * 1000
                self._log_target(best_center, cost_ms)
                continue

            if self.last_center is not None and self.lost_count < MAX_LOST_FRAMES:
                self.lost_count += 1
                predicted_x = self.last_center[0] + self.velocity[0]
                predicted_y = self.last_center[1] + self.velocity[1]
                self.last_center = (int(predicted_x), int(predicted_y))
                self._log_predict(self.last_center)
                continue

            self.last_center = None
            self.velocity = (0, 0)
            self.lost_count = 0
            if self.frame_idx % 30 == 0:
                self._log_lost()

    def run(self):
        self.camera.set_callback(self._callback)
        if not self.camera.open(
            main_size=FRAME_SIZE,
            fps=TARGET_FPS,
            enable_preview=True,
            use_manual_camera=USE_MANUAL_CAMERA,
            manual_exposure_us=MANUAL_EXPOSURE_US,
            manual_analog_gain=MANUAL_ANALOG_GAIN,
            frame_duration_us=FRAME_DURATION_US,
        ):
            print("摄像头启动失败，BlackSearch 无法运行。")
            return

        process_thread = threading.Thread(target=self._process_loop, daemon=True)
        process_thread.start()

        print("=" * 60)
        print("系统已进入 BlackSearch 运行模式")
        print("仅保留坐标输出，按 Ctrl+C 停止")
        print("=" * 60)

        try:
            while self.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n捕捉到 Ctrl+C，正在安全停止...")
            self.is_running = False

        process_thread.join(timeout=1.0)
        self.camera.close()


if __name__ == "__main__":
    UltimateHighSpeedTracker().run()
