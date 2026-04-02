# 主程序设计框图

## 1. 说明

本图描述当前工程的主程序结构、模块关系与运行时数据流。

## 2. 主程序结构图

```mermaid
flowchart TD
    A[程序入口<br/>app/BlackSearch.py] --> B[创建 UltimateHighSpeedTracker]
    B --> C[加载 CameraConfig]
    B --> D[加载 VofaSerialConfig]
    C --> E[初始化 Camera 驱动]
    D --> F[初始化 VOFA 串口驱动]

    E --> G[注册相机回调 _callback]
    F --> H{是否启用 VOFA}
    H -- 是 --> I[启动串口后台发送线程]
    H -- 否 --> J[跳过串口发送]

    G --> K[启动相机]
    K --> L[Picamera2 主图像流]
    L --> M[回调取帧并写入 frame_queue]

    M --> N[启动识别线程 _process_loop]
    N --> O[读取最新帧]
    O --> P[执行黑框检测与筛选]
    P --> Q{是否检测到目标}

    Q -- 是 --> R[更新中心坐标与速度]
    R --> S[输出 TARGET 日志]
    S --> T[更新 VOFA 最新数据]

    Q -- 否 --> U{是否进入短时预测}
    U -- 是 --> V[按速度外推预测坐标]
    V --> W[输出 PREDICT 日志]
    W --> T

    U -- 否 --> X[清空历史状态]
    X --> Y[输出 LOST 日志]
    Y --> T

    K --> Z[主线程保活]
    Z --> AA[等待 Ctrl+C]
    AA --> AB[关闭相机与串口]
```

## 3. 模块职责

### 3.1 应用层

[BlackSearch.py](/home/wrf/Desktop/25e/25etest/app/BlackSearch.py)

负责：

- 程序入口
- 相机配置与串口配置装配
- 识别流程控制
- 目标跟踪与预测
- 日志输出

### 3.2 相机驱动层

[camera.py](/home/wrf/Desktop/25e/25etest/Drivers/camera.py)

负责：

- 相机初始化
- 主图像流配置
- 3A / 手动曝光控制
- 预览显示
- 回调取帧

### 3.3 串口驱动层

[vofa_serial.py](/home/wrf/Desktop/25e/25etest/Drivers/vofa_serial.py)

负责：

- 串口初始化
- 后台定频发送
- 最新数据缓存
- 面向 VOFA+ 的文本格式输出

## 4. 运行特点

- 主线程负责生命周期管理
- 相机回调线程负责生产最新图像帧
- 识别线程负责消费图像帧并输出目标结果
- 串口发送线程负责低频发送最新数值数据

## 5. 说明

当前主程序采用“驱动层与应用层分离”的结构：

- 驱动层负责采集、控制、预览、串口发送
- 应用层负责识别逻辑与业务处理

该结构便于后续复用相机驱动与串口驱动，并降低不同任务之间的耦合度。
