# BlackSearch 识别处理链路

```mermaid
flowchart TD
    A[启动 Test/BlackSearch.py] --> B[创建 UltimateHighSpeedTracker]
    B --> C[初始化 Drivers/camera.py 中的 Camera]
    C --> D[打开 Picamera2 相机]
    D --> E[设置分辨率 1296x972]
    E --> F[设置手动曝光/增益/帧率]
    F --> G[注册帧回调 _callback]

    G --> H[相机产生 BGR 帧]
    H --> I[回调中复制最新帧]
    I --> J[清空旧队列帧]
    J --> K[仅保留最新一帧到 frame_queue]

    K --> L[处理线程 _process_loop 取帧]
    L --> M[更新处理帧率统计]
    M --> N{有历史目标且允许 ROI?}

    N -- 是 --> O[按上一帧中心和速度裁剪局部 ROI]
    N -- 否 --> P[直接使用整帧]
    O --> Q[缩小图像 scale=4]
    P --> Q

    Q --> R[转灰度]
    R --> S[高斯模糊]
    S --> T[BlackHat 形态学增强]
    T --> U[Otsu 二值化得到 mask]
    U --> V[查找轮廓 RETR_TREE]

    V --> W[遍历候选轮廓]
    W --> X[面积过滤]
    X --> Y[多边形顶点数过滤]
    Y --> Z[最小外接矩形边长/长宽比过滤]
    Z --> AA[填充率过滤]
    AA --> AB[查找最大子轮廓]
    AB --> AC[孔洞比例过滤]
    AC --> AD[中心黑度过滤]
    AD --> AE[换算回原图坐标]
    AE --> AF[结合历史位置计算评分]
    AF --> AG{是否当前最佳候选?}
    AG -- 是 --> AH[记录 best_center]
    AG -- 否 --> W
    AH --> AI[输出最终识别中心]

    AI --> AJ{识别到目标?}
    AJ -- 是 --> AK[更新 last_center 和 velocity]
    AK --> AL[输出 TARGET 坐标、耗时、FPS]

    AJ -- 否 --> AM{短时丢帧且未超过 MAX_LOST_FRAMES?}
    AM -- 是 --> AN[按上一帧速度做位置外推]
    AN --> AO[输出 PREDICT 坐标]
    AM -- 否 --> AP[清空历史目标与速度]
    AP --> AQ[周期性输出 LOST]
```

## 说明

- 相机输入来自 [camera.py](/home/wrf/Desktop/25e/25etest/Drivers/camera.py)，识别主流程在 [BlackSearch.py](/home/wrf/Desktop/25e/25etest/Test/BlackSearch.py)。
- 处理线程只消费“最新帧”，这是为了降低延迟，不追旧画面。
- ROI 裁剪用于减少整帧扫描开销，提高实时性。
- 候选目标的关键判定条件是：近似矩形、存在内孔洞、中心区域足够黑。
- 当目标短暂丢失时，程序不会立刻判定失败，而是先按上一帧速度做几帧预测。
