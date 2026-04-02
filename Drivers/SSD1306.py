import smbus
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class SSD1306_IIC():
    def __init__(self,iicDeviceIndex,address = 0x3c):
        self.IICInterface = smbus.SMBus(iicDeviceIndex)
        self.displayWidth = 128
        self.displayHeight = 64
        self.address = address
        self.framebuffer = np.zeros([1024,],dtype=np.uint8)
        self.initProcess()

    def clear(self,white=False):
        for i in range(1024):
            self.framebuffer[i] = 0xff if white else 0x00
        self.updateScreen()

    def close(self):
        self.IICInterface.close()

    def writeCommand(self,cmd):
        self.IICInterface.write_byte_data(self.address, 0x00, cmd)

    def writeData(self,data):
        self.IICInterface.write_byte_data(self.address, 0x40, data)

    def renderSinglePixel(self,x,y,value):
        if x < 0 or x >= self.displayWidth: return
        elif y < 0 or y >= self.displayHeight: return
        part = self.framebuffer[x + (y // 8) * self.displayWidth]
        if value:
            part |= 1 << (y%8)
        else:
            part &= ~(1<<(y%8))
        self.framebuffer[x + (y // 8) * self.displayWidth] = part

    def renderPillowImage(self, pillowImage):
        assert type(pillowImage) == Image.Image
        assert pillowImage.mode == '1'
        array = np.array(pillowImage)
        # print(array)
        for x in range(self.displayWidth):
            for y in range(self.displayHeight):
                self.renderSinglePixel(x,y,1 if array[y][x] else 0)
                # self.renderSinglePixel(x,y, array[y][x])
        self.updateScreen()
    
    def updateScreen(self):
        for i in range(8):
            self.writeCommand(0xb0+i)
            self.writeCommand(0x00)
            self.writeCommand(0x10)
            for j in range(self.displayWidth):
                self.writeData(self.framebuffer[i*self.displayWidth + j])

    def initProcess(self):
        self.writeCommand(0xae)
        self.writeCommand(0x20)
        self.writeCommand(0x10)
        self.writeCommand(0xb0)
        self.writeCommand(0xc8)
        self.writeCommand(0x00)
        self.writeCommand(0x10)
        self.writeCommand(0x40)
        self.writeCommand(0x81)
        self.writeCommand(0xff)
        self.writeCommand(0xa1)
        self.writeCommand(0xa6)
        self.writeCommand(0xa8)
        self.writeCommand(self.displayHeight - 1)
        self.writeCommand(0xa4)
        self.writeCommand(0xd3)
        self.writeCommand(0x00)
        self.writeCommand(0xd5)
        self.writeCommand(0xf0)
        self.writeCommand(0xd9)
        self.writeCommand(0x22)

        self.writeCommand(0xda)
        self.writeCommand(0x12)

        self.writeCommand(0xdb)
        self.writeCommand(0x40)
        self.writeCommand(0x8d)
        self.writeCommand(0x14)
        self.writeCommand(0xaf)



if __name__ == '__main__':
    ssd1306 = SSD1306_IIC(1)
    image = Image.new('1',(128,64),0)
    font = ImageFont.truetype('wqy-microhei.ttc',20)
    draw = ImageDraw.ImageDraw(image)
    # draw.line([(0,0),(127,63)],10)
    draw.text((0,0), 'Manba out!', fill=1, font=font)
    ssd1306.renderPillowImage(image)
    ssd1306.close()