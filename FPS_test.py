import cv2
import time

def test_fps():
    # 0 是默认 USB 摄像头
    cap = cv2.VideoCapture(0)
    
    # 强制设置分辨率，分辨率越高帧率越低
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("无法打开摄像头")
        return

    print("--- FPS 测试开始 (按 'q' 退出) ---")
    
    # 用于计算 FPS 的变量
    prev_time = 0
    
    while True:
        # 1. 纯粹的抓取，不做任何处理
        ret, frame = cap.read()
        if not ret:
            break

        # 2. 计算当前帧率
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time

        # 3. 仅在画面上打印一个数字
        cv2.putText(frame, f"FPS: {int(fps)}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 4. 显示画面
        cv2.imshow("Pure FPS Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_fps()