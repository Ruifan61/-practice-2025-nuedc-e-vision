# 树莓派部署指南

## 1. 传输代码到树莓派

### Windows上操作（PowerShell/CMD）
```bash
# 方法A：只传输测试脚本
scp "c:\Users\wrf\Desktop\nuedc\视觉代码(1)\视觉代码\quick_test.py" pi@树莓派IP:/home/pi/

# 方法B：传输整个项目（如果要用原始代码）
scp -r "c:\Users\wrf\Desktop\nuedc\视觉代码(1)\视觉代码" pi@树莓派IP:/home/pi/vision_code
```

## 2. 在树莓派上安装依赖

SSH连接到树莓派后：
```bash
ssh pi@树莓派IP
```

安装必要的Python库：
```bash
# 更新系统
sudo apt update

# 安装OpenCV和依赖
sudo apt install -y python3-opencv python3-numpy

# 如果使用Picamera2
sudo apt install -y python3-picamera2

# 如果使用USB摄像头，确保有权限
sudo usermod -a -G video $USER
```

## 3. 运行测试脚本

### 使用USB摄像头
```bash
cd ~
python3 quick_test.py --usb
```

### 使用Picamera2（树莓派官方摄像头）
```bash
python3 quick_test.py
```

### 指定USB摄像头ID（如果有多个摄像头）
```bash
python3 quick_test.py --usb --camera-id 0
```

## 4. 调试技巧

### 如果看不到窗口（无显示器）
需要通过VNC或X11转发：

**方法A：使用VNC**
```bash
# 在树莓派上启用VNC
sudo raspi-config
# 选择 Interface Options -> VNC -> Enable

# 然后用VNC Viewer连接树莓派
```

**方法B：X11转发（需要Windows安装Xming）**
```bash
# SSH时加上-X参数
ssh -X pi@树莓派IP
python3 quick_test.py --usb
```

### 如果摄像头无法打开
```bash
# 检查USB摄像头
ls /dev/video*

# 测试摄像头
v4l2-ctl --list-devices

# 给予权限
sudo chmod 666 /dev/video0
```

### 如果识别率低
1. 按 `d` 键开启调试模式，查看候选矩形
2. 按 `-` 键降低阈值（让图像更暗）
3. 调整光照条件
4. 确保目标是黑色矩形在白色背景上

## 5. 性能优化

如果帧率太低（<15fps）：
```python
# 编辑 quick_test.py，修改分辨率
RESOLUTION = (480, 270)  # 降低分辨率
```

## 6. 集成到原项目

如果要在原项目中使用优化后的算法：

### 替换 Algorithm/CenterGet.py 中的参数
```python
# 在 CenterGet 函数中修改
epsilon = 0.02 * perimeter  # 从0.01改为0.02
if area < 300:  # 从500改为300
if all(60 < angle < 120 for angle in angles):  # 从70-110改为60-120
if max(lengths) / min(lengths) <= 8:  # 从5改为8
```

### 或者直接替换整个识别函数
将 quick_test.py 中的 `find_rectangle()` 函数复制到你的代码中。

## 7. 常见问题

**Q: ImportError: No module named 'picamera2'**
A: 使用 `--usb` 参数改用USB摄像头

**Q: 画面卡顿**
A: 降低分辨率或帧率

**Q: 识别不到目标**
A:
- 按 `d` 开启调试模式
- 按 `-` 降低阈值
- 确保目标是黑色矩形
- 检查光照条件

**Q: 误识别率高**
A:
- 按 `+` 增加阈值
- 减小 ANGLE_RANGE
- 减小 EDGE_RATIO_MAX

## 8. 按键说明

- `q` - 退出程序
- `s` - 保存当前帧截图
- `+` - 增加二值化阈值（+5）
- `-` - 减少二值化阈值（-5）
- `d` - 切换调试模式

## 9. 快速测试命令

```bash
# 一键测试（USB摄像头）
cd ~ && python3 quick_test.py --usb

# 查看实时日志
python3 quick_test.py --usb 2>&1 | tee test.log
```
