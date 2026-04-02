# import os
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import cv2
# import numpy as np
# import math
# import time
# from Drivers.camera import Camera

# # ================= 运行模式参数 =================
# SHOW_GUI = False
# WINDOW_NAME = 'BlackSearch'
# MASK_WINDOW_NAME = 'Mask View'
# BLACKHAT_WINDOW_NAME = 'BlackHat View'

# WARMUP_TIME = 1.0
# WARMUP_FRAMES = 10
# # ===============================================

# # ================= 图像增强参数 =================
# USE_CLAHE = True
# CLAHE_CLIP_LIMIT = 2.0
# CLAHE_TILE_GRID = (8, 8)

# GAUSSIAN_KSIZE = 5
# BLACKHAT_KERNEL_SIZE = 11   # 必须是奇数，9~15 之间常用

# # 二值模式：
# # "blackhat_otsu"     -> 推荐
# # "blackhat_adaptive" -> 光照特别碎时再试
# BINARY_MODE = "blackhat_otsu"

# ADAPTIVE_BLOCK_SIZE = 31    # 必须是奇数
# ADAPTIVE_C = 2

# MORPH_CLOSE_KERNEL = 3
# MORPH_CLOSE_ITERS = 2
# MORPH_OPEN_KERNEL = 3
# MORPH_OPEN_ITERS = 1
# DILATE_ITERS = 1
# # ===============================================

# # ================= 目标几何参数 =================
# MIN_OUTER_AREA = 250
# MAX_OUTER_AREA = 6000

# MIN_SIDE = 12
# MAX_ASPECT_RATIO = 2.5
# OUTER_FILL_RATIO_MIN = 0.60

# HOLE_RATIO_MIN = 0.18
# HOLE_RATIO_MAX = 0.85
# CENTER_OFFSET_RATIO_MAX = 0.25

# APPROX_EPSILON_FACTOR = 0.03
# # ===============================================

# # ================= 跟踪参数 =================
# MAX_LOST_FRAMES = 5
# TRACK_DIST_WEIGHT = 0.8
# # ===============================================


# def ensure_odd(x):
#     return x if x % 2 == 1 else x + 1


# def get_contour_center(cnt):
#     m = cv2.moments(cnt)
#     if abs(m["m00"]) < 1e-6:
#         return None
#     cx = int(round(m["m10"] / m["m00"]))
#     cy = int(round(m["m01"] / m["m00"]))
#     return (cx, cy)


# def get_largest_child_index(contours, hierarchy, parent_idx):
#     """
#     找某个轮廓的最大子轮廓（同一层兄弟中面积最大的那个）
#     hierarchy: shape = (1, N, 4), [next, prev, first_child, parent]
#     """
#     first_child = hierarchy[0][parent_idx][2]
#     if first_child == -1:
#         return -1, 0.0

#     best_idx = -1
#     best_area = 0.0
#     child = first_child

#     while child != -1:
#         area = abs(cv2.contourArea(contours[child]))
#         if area > best_area:
#             best_area = area
#             best_idx = child
#         child = hierarchy[0][child][0]  # 下一个同级兄弟

#     return best_idx, best_area


# def preprocess_frame(frame, clahe):
#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     mean_gray = float(np.mean(gray))

#     if clahe is not None:
#         gray = clahe.apply(gray)

#     k = ensure_odd(GAUSSIAN_KSIZE)
#     blurred = cv2.GaussianBlur(gray, (k, k), 0)

#     bh_k = ensure_odd(BLACKHAT_KERNEL_SIZE)
#     bh_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (bh_k, bh_k))
#     blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, bh_kernel)

#     if BINARY_MODE == "blackhat_adaptive":
#         block = max(3, ensure_odd(ADAPTIVE_BLOCK_SIZE))
#         mask = cv2.adaptiveThreshold(
#             blackhat,
#             255,
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY,
#             block,
#             ADAPTIVE_C
#         )
#         used_threshold = -1
#         threshold_desc = "BH+ADAPT"
#     else:
#         used_threshold, mask = cv2.threshold(
#             blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
#         )
#         threshold_desc = "BH+OTSU"

#     close_kernel = cv2.getStructuringElement(
#         cv2.MORPH_RECT, (MORPH_CLOSE_KERNEL, MORPH_CLOSE_KERNEL)
#     )
#     mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=MORPH_CLOSE_ITERS)

#     if MORPH_OPEN_ITERS > 0:
#         open_kernel = cv2.getStructuringElement(
#             cv2.MORPH_RECT, (MORPH_OPEN_KERNEL, MORPH_OPEN_KERNEL)
#         )
#         mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=MORPH_OPEN_ITERS)

#     if DILATE_ITERS > 0:
#         mask = cv2.dilate(mask, close_kernel, iterations=DILATE_ITERS)

#     return gray, blackhat, mask, used_threshold, threshold_desc, mean_gray


# def find_best_target(mask, last_center):
#     contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

#     if hierarchy is None or len(contours) == 0:
#         return None, None, None

#     h, w = mask.shape[:2]
#     best = None
#     best_score = -1e18

#     for i, cnt in enumerate(contours):
#         outer_area = abs(cv2.contourArea(cnt))
#         if outer_area < MIN_OUTER_AREA or outer_area > MAX_OUTER_AREA:
#             continue

#         perimeter = cv2.arcLength(cnt, True)
#         if perimeter <= 0:
#             continue

#         approx = cv2.approxPolyDP(cnt, APPROX_EPSILON_FACTOR * perimeter, True)
#         if len(approx) < 4 or len(approx) > 8:
#             continue

#         rect = cv2.minAreaRect(cnt)
#         (cx, cy), (rw, rh), angle = rect

#         if rw < MIN_SIDE or rh < MIN_SIDE:
#             continue

#         rect_area = rw * rh
#         if rect_area <= 1:
#             continue

#         aspect_ratio = max(rw, rh) / max(1.0, min(rw, rh))
#         if aspect_ratio > MAX_ASPECT_RATIO:
#             continue

#         fill_ratio = outer_area / rect_area
#         if fill_ratio < OUTER_FILL_RATIO_MIN:
#             continue

#         child_idx, hole_area = get_largest_child_index(contours, hierarchy, i)
#         if child_idx == -1:
#             continue

#         hole_ratio = hole_area / outer_area
#         if hole_ratio < HOLE_RATIO_MIN or hole_ratio > HOLE_RATIO_MAX:
#             continue

#         child_cnt = contours[child_idx]
#         child_perimeter = cv2.arcLength(child_cnt, True)
#         if child_perimeter <= 0:
#             continue

#         child_approx = cv2.approxPolyDP(child_cnt, APPROX_EPSILON_FACTOR * child_perimeter, True)
#         if len(child_approx) < 4 or len(child_approx) > 8:
#             continue

#         inner_rect = cv2.minAreaRect(child_cnt)
#         (icx, icy), (iw, ih), _ = inner_rect
#         if iw < 4 or ih < 4:
#             continue

#         inner_aspect = max(iw, ih) / max(1.0, min(iw, ih))
#         if inner_aspect > MAX_ASPECT_RATIO:
#             continue

#         center_offset = math.hypot(icx - cx, icy - cy)
#         if center_offset > CENTER_OFFSET_RATIO_MAX * min(rw, rh):
#             continue

#         cxi = int(round(cx))
#         cyi = int(round(cy))
#         if not (0 <= cxi < w and 0 <= cyi < h):
#             continue

#         # 空心框中心应该是黑色
#         if mask[cyi, cxi] != 0:
#             continue

#         score = outer_area + 250.0 * fill_ratio + 200.0 * hole_ratio

#         if last_center is not None:
#             dist = math.hypot(cx - last_center[0], cy - last_center[1])
#             score -= TRACK_DIST_WEIGHT * dist

#         if score > best_score:
#             best_score = score
#             box = cv2.boxPoints(rect).astype(int)
#             inner_box = cv2.boxPoints(inner_rect).astype(int)
#             best = {
#                 "center": (cxi, cyi),
#                 "outer_box": box,
#                 "inner_box": inner_box,
#                 "outer_area": outer_area,
#                 "hole_ratio": hole_ratio,
#                 "fill_ratio": fill_ratio,
#                 "angle": angle,
#             }

#     if best is None:
#         return None, None, None

#     return best, contours, hierarchy


# def detect_black_frame():
#     picam2 = Camera()
#     if not picam2.open():
#         print("摄像头打开失败。")
#         return

#     print("=" * 50)
#     print("相机预热中...")
#     time.sleep(WARMUP_TIME)
#     for _ in range(WARMUP_FRAMES):
#         _ = picam2.capture()
#     print("预热完成。")
#     print("=" * 50)

#     if USE_CLAHE:
#         clahe = cv2.createCLAHE(
#             clipLimit=CLAHE_CLIP_LIMIT,
#             tileGridSize=CLAHE_TILE_GRID
#         )
#     else:
#         clahe = None

#     if SHOW_GUI:
#         cv2.namedWindow(WINDOW_NAME)
#         cv2.namedWindow(MASK_WINDOW_NAME)
#         cv2.namedWindow(BLACKHAT_WINDOW_NAME)

#     last_center = None
#     velocity = (0, 0)
#     lost_count = 0

#     prev_time = time.time()
#     fps_smooth = 0.0

#     print("=" * 50)
#     print("目标追踪已启动")
#     print(f"模式: {'调试模式(带GUI)' if SHOW_GUI else '比赛模式(无GUI)'}")
#     print(f"检测链路: {BINARY_MODE} + RETR_TREE")
#     print("提示: 按 Ctrl+C 或 GUI 模式下按 'q' 退出")
#     print("=" * 50)

#     try:
#         while True:
#             frame = picam2.capture()
#             if frame is None:
#                 print("读取图像失败，退出。")
#                 break

#             gray, blackhat, mask, used_threshold, threshold_desc, mean_gray = preprocess_frame(frame, clahe)

#             best, contours, hierarchy = find_best_target(mask, last_center)

#             h, w = frame.shape[:2]

#             if best is not None:
#                 best_center = best["center"]

#                 if last_center is not None and lost_count == 0:
#                     velocity = (
#                         best_center[0] - last_center[0],
#                         best_center[1] - last_center[1]
#                     )

#                 last_center = best_center
#                 lost_count = 0
#                 status_str = f"TARGET  | X: {best_center[0]:3d}, Y: {best_center[1]:3d}"

#                 if SHOW_GUI:
#                     cv2.drawContours(frame, [best["outer_box"]], -1, (0, 255, 0), 2)
#                     cv2.drawContours(frame, [best["inner_box"]], -1, (255, 255, 0), 1)
#                     cv2.circle(frame, best_center, 6, (0, 0, 255), -1)
#                     cv2.putText(
#                         frame, "TARGET",
#                         (best_center[0] + 10, best_center[1]),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
#                     )

#             else:
#                 if last_center is not None and lost_count < MAX_LOST_FRAMES:
#                     lost_count += 1

#                     pred_x = last_center[0] + velocity[0]
#                     pred_y = last_center[1] + velocity[1]

#                     pred_x = max(0, min(w - 1, pred_x))
#                     pred_y = max(0, min(h - 1, pred_y))
#                     predicted_center = (int(pred_x), int(pred_y))

#                     last_center = predicted_center
#                     status_str = f"PREDICT | X: {predicted_center[0]:3d}, Y: {predicted_center[1]:3d}"

#                     if SHOW_GUI:
#                         cv2.circle(frame, predicted_center, 6, (0, 255, 255), -1)
#                         cv2.putText(
#                             frame, f"PREDICT ({lost_count})",
#                             (predicted_center[0] + 10, predicted_center[1]),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
#                         )
#                 else:
#                     last_center = None
#                     velocity = (0, 0)
#                     lost_count = 0
#                     status_str = "LOST    | X: ---, Y: ---"

#                     if SHOW_GUI:
#                         cv2.putText(
#                             frame, "LOST", (10, 30),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
#                         )

#             current_time = time.time()
#             dt = current_time - prev_time
#             prev_time = current_time

#             fps = 1.0 / dt if dt > 0 else 0.0
#             if fps_smooth == 0.0:
#                 fps_smooth = fps
#             else:
#                 fps_smooth = fps_smooth * 0.8 + fps * 0.2

#             if best is not None:
#                 if used_threshold >= 0:
#                     threshold_text = f"{used_threshold:.0f}"
#                 else:
#                     threshold_text = "ADAPTIVE"

#                 print(
#                     f"[STATUS] {status_str} | FPS: {fps_smooth:4.1f} | "
#                     f"mean_gray: {mean_gray:.1f} | th: {threshold_text} | "
#                     f"mode: {threshold_desc} | area: {best['outer_area']:.0f} | "
#                     f"hole: {best['hole_ratio']:.2f}",
#                     flush=True
#                 )

#             if SHOW_GUI:
#                 cv2.putText(
#                     frame, f"Mode: {threshold_desc}", (10, h - 85),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
#                 )

#                 if used_threshold >= 0:
#                     th_show = f"Th: {used_threshold:.0f}"
#                 else:
#                     th_show = "Th: ADAPTIVE"

#                 cv2.putText(
#                     frame, th_show, (10, h - 60),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
#                 )
#                 cv2.putText(
#                     frame, f"GrayMean: {mean_gray:.1f}", (10, h - 35),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
#                 )
#                 cv2.putText(
#                     frame, f"FPS: {fps_smooth:.1f}", (10, h - 10),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2
#                 )

#                 cv2.imshow(WINDOW_NAME, frame)
#                 cv2.imshow(MASK_WINDOW_NAME, mask)
#                 cv2.imshow(BLACKHAT_WINDOW_NAME, blackhat)

#                 key = cv2.waitKey(1) & 0xFF
#                 if key == ord('q'):
#                     print("\n退出检测。")
#                     break

#     except KeyboardInterrupt:
#         print("\n收到 Ctrl+C，退出检测。")

#     finally:
#         picam2.close()
#         if SHOW_GUI:
#             cv2.destroyAllWindows()


# if __name__ == '__main__':
#     detect_black_frame()

import os
import sys
import math
import time
import threading
import queue
import datetime
import cv2
import numpy as np
from picamera2 import Picamera2, MappedArray

# 自动处理 DRM 预览驱动
try:
    try:
        from picamera2.preview import DrmPreview
    except ImportError:
        from picamera2.previews import DrmPreview
except ImportError:
    DrmPreview = None

# ================= 核心配置 =================
FRAME_SIZE = (1296, 972)
TARGET_FPS = 60

# 相机硬件控制
USE_MANUAL_CAMERA = True
MANUAL_EXPOSURE_US = 4000
MANUAL_ANALOG_GAIN = 8.0
FRAME_DURATION_US = int(1_000_000 / TARGET_FPS)

# 算法识别参数
DETECT_SCALE = 4
USE_TRACKING_ROI = True
ROI_HALF_SIZE = 120
MAX_LOST_FRAMES = 5
TRACK_DIST_WEIGHT = 0.8
FULL_FRAME_RESCAN_INTERVAL = 48

# 几何过滤参数 (严谨版)
MIN_OUTER_AREA = 250
MAX_OUTER_AREA = 50000
MIN_SIDE = 12
MAX_ASPECT_RATIO = 3.6
OUTER_FILL_RATIO_MIN = 0.42
HOLE_RATIO_MIN = 0.12
HOLE_RATIO_MAX = 0.85
CENTER_OFFSET_RATIO_MAX = 0.40
APPROX_EPSILON_FACTOR = 0.03
MIN_APPROX_VERTICES = 4
MAX_APPROX_VERTICES = 12
CENTER_BLACK_PATCH = 5
CENTER_BLACK_MEAN_MAX = 60
# ============================================

def get_largest_child_index(contours, hierarchy, parent_idx):
    first_child = hierarchy[0][parent_idx][2]
    if first_child == -1: return -1, 0.0
    best_idx, best_area, child = -1, 0.0, first_child
    while child != -1:
        area = abs(cv2.contourArea(contours[child]))
        if area > best_area:
            best_area = area
            best_idx = child
        child = hierarchy[0][child][0]
    return best_idx, best_area

def get_center_black_mean(mask, cx, cy, patch_size):
    half = max(1, patch_size // 2)
    y0, y1 = max(0, cy - half), min(mask.shape[0], cy + half + 1)
    x0, x1 = max(0, cx - half), min(mask.shape[1], cx + half + 1)
    if x1 <= x0 or y1 <= y0: return 255.0
    return float(np.mean(mask[y0:y1, x0:x1]))

class UltimateHighSpeedTracker:
    def __init__(self):
        self.picam2 = Picamera2()
        self.last_center = None
        self.velocity = (0, 0)
        self.lost_count = 0
        self.frame_idx = 0
        self.is_running = True
        
        # 帧队列：只取最新帧
        self.frame_queue = queue.Queue(maxsize=1)
        
        # 帧率统计变量
        self.fps_start_time = time.perf_counter()
        self.fps_frame_count = 0
        self.current_fps = 0.0

    def _callback(self, request):
        with MappedArray(request, "main") as m:
            bgr_array = m.array.copy()
        
        # 清空积压，永远只处理最新的一帧，杜绝延迟拖影
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        self.frame_queue.put(bgr_array)

    def _process_loop(self):
        while self.is_running:
            try:
                frame_bgr = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # 计算处理帧率 (1秒滑动平均)
            now = time.perf_counter()
            self.fps_frame_count += 1
            elapsed = now - self.fps_start_time
            if elapsed >= 1.0:
                self.current_fps = self.fps_frame_count / elapsed
                self.fps_frame_count = 0
                self.fps_start_time = now

            self.frame_idx += 1
            t0 = time.perf_counter()
            h, w = frame_bgr.shape[:2]
            
            # --- 1. ROI 动态裁剪 ---
            search_frame = frame_bgr
            ox, oy = 0, 0
            if (USE_TRACKING_ROI and self.last_center and self.lost_count <= 2 
                and self.frame_idx % FULL_FRAME_RESCAN_INTERVAL != 0):
                px, py = self.last_center[0] + self.velocity[0], self.last_center[1] + self.velocity[1]
                x0, y0 = max(0, int(px - ROI_HALF_SIZE)), max(0, int(py - ROI_HALF_SIZE))
                x1, y1 = min(w, int(px + ROI_HALF_SIZE)), min(h, int(py + ROI_HALF_SIZE))
                if x1 - x0 > 20 and y1 - y0 > 20:
                    search_frame = frame_bgr[y0:y1, x0:x1]
                    ox, oy = x0, y0

            # --- 2. 图像预处理 ---
            scale = DETECT_SCALE
            small = cv2.resize(search_frame, (search_frame.shape[1]//scale, search_frame.shape[0]//scale))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            bh_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
            blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, bh_kernel)
            _, mask = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # --- 3. 严格几何过滤 ---
            contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            best_info = None
            best_score = -1e12
            
            if hierarchy is not None:
                for i, cnt in enumerate(contours):
                    outer_area = abs(cv2.contourArea(cnt))
                    if not ((MIN_OUTER_AREA/(scale**2)) < outer_area < (MAX_OUTER_AREA/(scale**2))): continue
                    
                    perimeter = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, APPROX_EPSILON_FACTOR * perimeter, True)
                    if not (MIN_APPROX_VERTICES <= len(approx) <= MAX_APPROX_VERTICES): continue
                    
                    rect = cv2.minAreaRect(cnt)
                    (cx, cy), (rw, rh), _ = rect
                    if rw < (MIN_SIDE/scale) or rh < (MIN_SIDE/scale): continue
                    
                    aspect_ratio = max(rw, rh) / max(1.0, min(rw, rh))
                    if aspect_ratio > MAX_ASPECT_RATIO: continue
                    if (outer_area / (rw * rh)) < OUTER_FILL_RATIO_MIN: continue
                    
                    # 子轮廓/孔洞检测
                    child_idx, hole_area = get_largest_child_index(contours, hierarchy, i)
                    if child_idx == -1: continue
                    if not (HOLE_RATIO_MIN < (hole_area/outer_area) < HOLE_RATIO_MAX): continue
                    
                    # 黑度校验
                    if get_center_black_mean(mask, int(cx), int(cy), CENTER_BLACK_PATCH) > CENTER_BLACK_MEAN_MAX: continue
                    
                    # 最终打分与中心转换
                    global_cx, global_cy = (cx * scale) + ox, (cy * scale) + oy
                    score = outer_area
                    if self.last_center:
                        dist = math.hypot(global_cx - self.last_center[0], global_cy - self.last_center[1])
                        score -= dist * TRACK_DIST_WEIGHT
                    
                    if score > best_score:
                        best_score = score
                        best_info = (int(global_cx), int(global_cy), cnt, ox, oy)

            # --- 4. 终端日志输出 (纯净版) ---
            if best_info:
                cx, cy, cnt, box_ox, box_oy = best_info
                
                # 更新追踪向量
                if self.last_center:
                    self.velocity = (cx - self.last_center[0], cy - self.last_center[1])
                self.last_center = (cx, cy)
                self.lost_count = 0
                
                proc_ms = (time.perf_counter() - t0) * 1000
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [TARGET] X:{cx:3d} Y:{cy:3d} | 耗时:{proc_ms:3.0f}ms | 帧率: {self.current_fps:4.1f} FPS")
            else:
                # 预测/丢失逻辑
                if self.last_center and self.lost_count < MAX_LOST_FRAMES:
                    self.lost_count += 1
                    self.last_center = (self.last_center[0] + self.velocity[0], self.last_center[1] + self.velocity[1])
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [PREDICT] X:{int(self.last_center[0]):3d} Y:{int(self.last_center[1]):3d} | 帧率: {self.current_fps:4.1f} FPS")
                else:
                    self.last_center, self.velocity, self.lost_count = None, (0, 0), 0
                    if self.frame_idx % 30 == 0:
                        print(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [LOST] 等待目标... | 帧率: {self.current_fps:4.1f} FPS")

    def run(self):
        # 1. 启动硬件预览 (底层 60FPS)
        if DrmPreview:
            self.picam2.start_preview(DrmPreview())
        
        # 2. 相机流配置 (BGR888)
        config = self.picam2.create_video_configuration(main={"size": FRAME_SIZE, "format": "BGR888"})
        self.picam2.configure(config)
        self.picam2.post_callback = self._callback
        
        # 3. 硬件参数锁定
        if USE_MANUAL_CAMERA:
            self.picam2.set_controls({
                "AeEnable": False,
                "FrameDurationLimits": (FRAME_DURATION_US, FRAME_DURATION_US),
                "ExposureTime": MANUAL_EXPOSURE_US,
                "AnalogueGain": MANUAL_ANALOG_GAIN,
            })
        
        self.picam2.start()
        
        # 4. 开启异步处理线程
        process_thread = threading.Thread(target=self._process_loop, daemon=True)
        process_thread.start()

        print("=" * 60)
        print("🚀 系统已进入【战斗部署模式】！")
        print("已关闭所有图像渲染，全力输出追踪坐标 (预期 50+ FPS)")
        print("按 Ctrl+C 停止运行")
        print("=" * 60)

        try:
            while self.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n捕捉到 Ctrl+C，正在安全停止...")
            self.is_running = False
        
        self.picam2.stop()

if __name__ == "__main__":
    app = UltimateHighSpeedTracker()
    app.run()