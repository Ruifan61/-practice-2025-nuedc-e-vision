# 相机驱动移植说明

## 1. 目标

将当前相机驱动层移植到新的工程中，并保持驱动层与应用层解耦。

## 2. 最小文件集合

移植时至少保留以下文件：

- [camera.py](/home/wrf/Desktop/25e/25etest/Drivers/camera.py)
- [__init__.py](/home/wrf/Desktop/25e/25etest/Drivers/__init__.py)

## 3. 依赖项

运行环境需具备以下依赖：

- Python 3
- `opencv-python`
- `numpy`
- `picamera2`
- `libcamera`

树莓派环境需保证：

- 摄像头硬件连接正常
- `libcamera` 服务可用
- DRM/KMS 显示链路可用（如需 `DrmPreview` 预览）

## 4. 代码结构

[camera.py](/home/wrf/Desktop/25e/25etest/Drivers/camera.py) 负责：

- 相机初始化
- `Picamera2` 配置
- 3A / 手动曝光控制
- 预览窗口配置
- 回调取帧
- 同步抓帧接口

驱动层通过 `CameraConfig` 暴露配置项，不要求应用层直接操作 `Picamera2` 细节。

## 5. 移植步骤

### 5.1 复制文件

将以下目录结构复制到目标工程：

```text
Drivers/
  __init__.py
  camera.py
```

### 5.2 保证导入路径正确

确保目标工程中以下导入可用：

```python
from Drivers.camera import Camera, CameraConfig
```

### 5.3 配置相机参数

在应用层通过 `CameraConfig` 配置相机行为。例如：

```python
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
)
```

常用配置说明：

- `main_size`
  识别输入分辨率
- `fps`
  目标帧率
- `enable_preview`
  是否启用 `DrmPreview`
- `preview_fullscreen`
  是否铺满显示器
- `use_manual_camera`
  是否启用手动曝光模式
- `enable_3a`
  是否启用自动曝光链路
- `enable_awb`
  是否启用自动白平衡
- `enable_af`
  是否启用自动对焦

### 5.4 根据硬件能力调整

不同相机模组能力不同，移植时需检查：

- 是否支持 AF
- 是否支持指定分辨率和帧率
- 是否支持当前显示模式

如模组不支持 AF，驱动层会自动退化为 `AE/AWB`。

## 6. 手动模式与 3A 模式

### 6.1 3A 模式

适用于环境光变化较大的场景：

```python
CameraConfig(
    use_manual_camera=False,
    enable_3a=True,
    enable_awb=True,
    enable_af=False,
)
```

### 6.2 手动模式

适用于固定光照、要求识别稳定性的场景：

```python
CameraConfig(
    use_manual_camera=True,
    manual_exposure_us=4000,
    manual_analog_gain=8.0,
    frame_duration_us=16666,
)
```

## 7. 显示与识别关系

当前驱动设计中：

- 预览显示链路由 `DrmPreview` 负责
- 识别链路由 `post_callback -> queue -> _process_loop` 负责

预览链路与业务处理链路共享同一条主图像流，但逻辑相互独立。

## 8. 验证方法

移植完成后，先执行语法检查：

```bash
python3 -m py_compile Drivers/camera.py
```

再在目标工程入口中执行运行验证。

最小验证示例：

```python
from Drivers.camera import Camera, CameraConfig

config = CameraConfig()
camera = Camera(config)
camera.open()
```

检查以下内容：

- 相机是否成功启动
- 预览是否正常显示
- 回调或抓帧接口是否正常工作

## 9. 建议

- 驱动层仅负责采集、控制和预览
- 不在应用层直接调用 `Picamera2` 原始控制接口
- 新任务复用相机能力时，优先复用 `CameraConfig + Camera`
