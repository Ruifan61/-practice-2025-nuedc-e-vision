import serial
import struct


SERIAL_ID = "/dev/ttyAMA0"


class CarControl:
    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout=1)
        
    def send_angle(self, int1, int2):
        data_str = f"{int1},{int2},{0},{0}\n"
        # 编码为字节并发送
        self.ser.write(data_str.encode('utf-8'))

    def send_none(self):
        data_str = f"{404},{404},{0},{0}\n"
        # 编码为字节并发送
        self.ser.write(data_str.encode('utf-8'))

    def send_speed(self, int1, int2):
        data_str = f"{333},{333},{int1},{int2}\n"
        # 编码为字节并发送
        self.ser.write(data_str.encode('utf-8'))

    def send_off(self):
        data_str = f"{666},{666},{0},{0}\n"
        # 编码为字节并发送
        self.ser.write(data_str.encode('utf-8'))

    def __del__(self):
        self.ser.close()