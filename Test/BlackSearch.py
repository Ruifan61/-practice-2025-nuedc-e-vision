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

from Drivers.camera import Camera, CameraConfig
from Drivers.vofa_serial import VofaSerial, VofaSerialConfig


# 相机相关配置下沉到驱动配置对象里，应用层只声明自己需要的相机行为。
CAMERA_CONFIG = CameraConfig(
    main_size=(640, 480),
    fps=60,
    enable_preview=True,
    preview_fullscreen=True,
    use_manual_camera=False,
    enable_3a=True,
    enable_awb=True,
    enable_af=False,
    af_mode="continuous",
    manual_exposure_us=4000,
    manual_analog_gain=8.0,
    frame_duration_us=int(1_000_000 / 60),
)

VOFA_ENABLE = True
VOFA_CONFIG = VofaSerialConfig(
    port="/dev/serial0",
    baudrate=115200,
    send_hz=20.0,
)

# 跟踪参数：用于在“已经找到过目标”的前提下缩小搜索范围。
DETECT_SCALE = 4
USE_TRACKING_ROI = True
ROI_HALF_SIZE = 120
MAX_LOST_FRAMES = 5
TRACK_DIST_WEIGHT = 0.8
FULL_FRAME_RESCAN_INTERVAL = 48

# 几何参数：描述我们心里期望的黑框长什么样。
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
    # 在 RETR_TREE 模式下，每个轮廓都能知道自己的“子轮廓”。
    # 黑框识别很依赖这个层级关系，因为目标应当存在内孔洞。
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
    # 黑框中心在二值图里应该接近黑色（均值低）。
    # 这里不是只看单个像素，而是看一个小 patch，抗噪声更强。
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
        self.camera = Camera(CAMERA_CONFIG)
        self.vofa = VofaSerial(VOFA_CONFIG) if VOFA_ENABLE else None
        # last_center / velocity / lost_count 共同构成一个轻量级追踪器：
        # 找到目标时更新位置和速度，短时丢失时靠速度外推顶几帧。
        self.last_center = None
        self.velocity = (0, 0)
        self.lost_count = 0
        self.frame_idx = 0
        self.is_running = True
        # maxsize=1 的核心思想是“只认最新帧，不补历史帧”，
        # 这样识别结果永远尽量贴近当前真实画面。
        self.frame_queue = queue.Queue(maxsize=1)

        self.fps_start_time = time.perf_counter()
        self.fps_frame_count = 0
        self.current_fps = 0.0

    def _callback(self, bgr_array):
        # 相机线程比识别线程更快时，旧帧会堆积。
        # 这里主动丢掉旧帧，换来更低延迟和更自然的实时追踪体验。
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
            # 没有历史目标、刚丢目标、或定期全局复扫时，必须回到整帧搜索。
            return search_frame, offset_x, offset_y

        # 根据上一帧位置和速度做局部搜索，大幅降低整帧扫描开销。
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
        # 整个识别函数的目标只有一个：在当前帧里选出“最像黑框”的中心点。
        search_frame, offset_x, offset_y = self._build_search_frame(frame_bgr)

        scale = DETECT_SCALE
        # 先降采样再做形态学和轮廓分析，用分辨率换吞吐量。
        small_w = max(1, search_frame.shape[1] // scale)
        small_h = max(1, search_frame.shape[0] // scale)
        small = cv2.resize(search_frame, (small_w, small_h))

        # 处理链路：
        # 1. 灰度化，去掉颜色信息，只保留亮度结构；
        # 2. 高斯模糊，压掉高频噪声；
        # 3. BlackHat，专门增强“亮背景里的暗目标边缘”；
        # 4. Otsu，自动找阈值，得到候选黑框区域。
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        blackhat_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, blackhat_kernel)
        _, mask = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # RETR_TREE 会保留轮廓父子关系，这正是后面判断“空心框”的基础。
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            return None

        best_center = None
        best_score = -1e12
        min_area = MIN_OUTER_AREA / (scale ** 2)
        max_area = MAX_OUTER_AREA / (scale ** 2)

        for index, contour in enumerate(contours):
            outer_area = abs(cv2.contourArea(contour))
            # 面积是最快的一层粗筛，把过小噪声和过大块状区域先去掉。
            if not (min_area < outer_area < max_area):
                continue

            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, APPROX_EPSILON_FACTOR * perimeter, True)
            # 目标是近似矩形空心框，顶点数过少或过多都直接过滤。
            if not (MIN_APPROX_VERTICES <= len(approx) <= MAX_APPROX_VERTICES):
                continue

            rect = cv2.minAreaRect(contour)
            (cx, cy), (rw, rh), _ = rect
            if rw < (MIN_SIDE / scale) or rh < (MIN_SIDE / scale):
                continue

            # 黑框虽然可能有旋转，但整体应接近矩形，不应细长到离谱。
            aspect_ratio = max(rw, rh) / max(1.0, min(rw, rh))
            if aspect_ratio > MAX_ASPECT_RATIO:
                continue

            rect_area = rw * rh
            if rect_area <= 0:
                continue
            # fill_ratio 太低说明这个轮廓更像破碎边缘或杂乱噪声，不像完整框体。
            if (outer_area / rect_area) < OUTER_FILL_RATIO_MIN:
                continue

            child_idx, hole_area = get_largest_child_index(contours, hierarchy, index)
            if child_idx == -1:
                continue

            # 黑框的核心特征是“外轮廓 + 内孔洞”，没有孔洞的候选直接淘汰。
            hole_ratio = hole_area / outer_area
            if not (HOLE_RATIO_MIN < hole_ratio < HOLE_RATIO_MAX):
                continue

            # 中心区域应该足够黑，否则大概率是误检的普通深色块。
            if get_center_black_mean(mask, int(cx), int(cy), CENTER_BLACK_PATCH) > CENTER_BLACK_MEAN_MAX:
                continue

            # 轮廓分析是在缩小图和 ROI 内完成的，最终必须映射回原始整帧坐标。
            global_cx = (cx * scale) + offset_x
            global_cy = (cy * scale) + offset_y
            score = outer_area
            if self.last_center is not None:
                # 有历史目标时优先选择离上一帧更近的候选，保持追踪稳定。
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
        if self.vofa is not None:
            self.vofa.update_latest(center[0], center[1], round(self.current_fps, 2))

    def _log_predict(self, center):
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(
            f"[{now}] [PREDICT] X:{center[0]:3d} Y:{center[1]:3d} | "
            f"帧率: {self.current_fps:4.1f} FPS"
        )
        if self.vofa is not None:
            self.vofa.update_latest(center[0], center[1], round(self.current_fps, 2))

    def _log_lost(self):
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{now}] [LOST] 等待目标... | 帧率: {self.current_fps:4.1f} FPS")
        if self.vofa is not None:
            self.vofa.update_latest(-1, -1, round(self.current_fps, 2))

    def _process_loop(self):
        while self.is_running:
            try:
                frame_bgr = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # 这里统计的是“真正完成识别处理的帧率”，不是纯相机采集帧率。
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
                # 只有检测成功时才更新速度，避免把错误预测继续传播下去。
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
                # 短时丢帧时沿上一帧速度做外推，减小目标闪断带来的抖动。
                predicted_x = self.last_center[0] + self.velocity[0]
                predicted_y = self.last_center[1] + self.velocity[1]
                self.last_center = (int(predicted_x), int(predicted_y))
                self._log_predict(self.last_center)
                continue

            # 丢失超过阈值后彻底清空历史状态，让下一次识别重新从整帧开始。
            self.last_center = None
            self.velocity = (0, 0)
            self.lost_count = 0
            if self.frame_idx % 30 == 0:
                self._log_lost()

    def run(self):
        # Camera 内部会把 Picamera2 的 post_callback 挂到这里；
        # 也就是“相机线程产帧 -> _callback 入队 -> 处理线程识别”这条链路。
        if self.vofa is not None and not self.vofa.start():
            print("VOFA 串口启动失败，已跳过串口发送。")
            self.vofa = None

        self.camera.set_callback(self._callback)
        if not self.camera.open():
            print("摄像头启动失败，BlackSearch 无法运行。")
            if self.vofa is not None:
                self.vofa.close()
            return

        # 识别放到独立线程里，主线程只负责保活和响应 Ctrl+C。
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
        if self.vofa is not None:
            self.vofa.close()


if __name__ == "__main__":
    UltimateHighSpeedTracker().run()
