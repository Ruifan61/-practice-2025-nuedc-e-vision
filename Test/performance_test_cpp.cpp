#include <opencv2/opencv.hpp>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

using Clock = std::chrono::steady_clock;

struct SharedFrame {
    cv::Mat frame;
    Clock::time_point capture_time;
    uint64_t seq = 0;
    bool has_frame = false;
    std::mutex mtx;
};

static std::atomic<bool> g_running(true);

void signal_handler(int) {
    g_running = false;
}

int main() {
    std::signal(SIGINT, signal_handler);

    // =========================
    // 相机参数
    // =========================
    const int WIDTH = 640;
    const int HEIGHT = 480;
    const int TARGET_FPS = 60;

    // =========================
    // GStreamer 管线
    // 说明：
    // 1. libcamerasrc: 树莓派 libcamera 源
    // 2. format=BGR: 直接输出给 OpenCV 可用的 BGR
    // 3. appsink drop=true max-buffers=1: 只保留最新帧，不堆积
    // 4. sync=false: 不按显示时钟阻塞
    // =========================
    std::string pipeline =
        "libcamerasrc ! "
        "video/x-raw,width=" + std::to_string(WIDTH) +
        ",height=" + std::to_string(HEIGHT) +
        ",framerate=" + std::to_string(TARGET_FPS) + "/1,format=BGR ! "
        "appsink drop=true max-buffers=1 sync=false";

    cv::VideoCapture cap(pipeline, cv::CAP_GSTREAMER);
    if (!cap.isOpened()) {
        std::cerr << "Failed to open camera with pipeline:\n" << pipeline << std::endl;
        return 1;
    }

    SharedFrame shared;

    std::atomic<uint64_t> capture_count{0};
    std::atomic<uint64_t> process_count{0};
    std::atomic<double> latest_latency_ms{0.0};

    // =========================
    // 采集线程
    // 始终只更新最新帧
    // =========================
    std::thread capture_thread([&]() {
        uint64_t local_seq = 0;

        while (g_running) {
            cv::Mat frame;
            if (!cap.read(frame)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;
            }

            auto now = Clock::now();

            {
                std::lock_guard<std::mutex> lock(shared.mtx);
                shared.frame = frame.clone();   // 独立拷贝，避免底层缓冲复用问题
                shared.capture_time = now;
                shared.seq = ++local_seq;
                shared.has_frame = true;
            }

            capture_count++;
        }
    });

    // =========================
    // 处理线程
    // 只处理最新帧，不处理旧帧
    // =========================
    std::thread process_thread([&]() {
        uint64_t last_seq = 0;

        while (g_running) {
            cv::Mat frame;
            Clock::time_point capture_time;
            uint64_t seq = 0;

            {
                std::lock_guard<std::mutex> lock(shared.mtx);
                if (!shared.has_frame || shared.seq == last_seq) {
                    // 没有新帧
                } else {
                    frame = shared.frame.clone();
                    capture_time = shared.capture_time;
                    seq = shared.seq;
                }
            }

            if (frame.empty() || seq == 0 || seq == last_seq) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                continue;
            }

            last_seq = seq;

            auto process_begin = Clock::now();
            double latency_ms = std::chrono::duration<double, std::milli>(
                process_begin - capture_time).count();
            latest_latency_ms.store(latency_ms, std::memory_order_relaxed);

            // =========================
            // 在这里写你的识别算法
            // 现在先留空，不做任何处理
            // 例如以后你可以加：
            // cv::cvtColor(...)
            // cv::threshold(...)
            // cv::findContours(...)
            // =========================

            process_count++;
        }
    });

    // =========================
    // 统计打印线程
    // 每秒打印一次实时统计
    // =========================
    std::thread stats_thread([&]() {
        uint64_t last_capture = 0;
        uint64_t last_process = 0;
        auto last_time = Clock::now();

        while (g_running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1000));

            auto now = Clock::now();
            double dt = std::chrono::duration<double>(now - last_time).count();

            uint64_t cur_capture = capture_count.load(std::memory_order_relaxed);
            uint64_t cur_process = process_count.load(std::memory_order_relaxed);

            double capture_fps = (cur_capture - last_capture) / dt;
            double process_fps = (cur_process - last_process) / dt;
            double latency_ms = latest_latency_ms.load(std::memory_order_relaxed);

            std::cout
                << "capture_fps=" << capture_fps
                << " | process_fps=" << process_fps
                << " | latency_ms=" << latency_ms
                << std::endl;

            last_capture = cur_capture;
            last_process = cur_process;
            last_time = now;
        }
    });

    std::cout << "Running... Press Ctrl+C to quit." << std::endl;

    capture_thread.join();
    process_thread.join();
    stats_thread.join();

    cap.release();
    std::cout << "Stopped." << std::endl;
    return 0;
}