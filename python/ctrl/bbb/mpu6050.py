import warnings
import math
import struct

if __name__ == "__main__":

    import sys
    sys.path.append('.')

import ctrl.block as block
import pycomms.mpu6050 as mpu6050

import numpy

class Quaternion:

    def __init__(self, w = 0, x = 0, y = 0, z = 1):
        self.x = float(x);
        self.y = float(y);
        self.z = float(z);
        self.w = float(w);

    def rotation(self):

        R = numpy.array(
            [[1 - 2*(self.y * self.y + self.z * self.z),
              2*(self.x * self.y - self.z * self.w),
              2*(self.x * self.z + self.y * self.w)],
             [2*(self.x * self.y + self.z * self.w),
              1 - 2*(self.x * self.x + self.z * self.z),
              2*(self.y * self.z - self.x * self.w)],
             [2*(self.x * self.z - self.y * self.w),
              2*(self.y * self.z + self.x * self.w),
              1 - 2*(self.x * self.x + self.y * self.y)]])

        return R

    def __str__(self):
        return "x:{:+5.4f} y:{:+5.4f} z:{:+5.4f} w:{:+5.4f}".format(self.x,self.y,self.z,self.w)


class Raw(block.Block):

    def __init__(self, *vars, **kwargs):

        # Sensor initialization
        self.mpu = mpu6050.MPU6050()
        self.mpu.initialize()

        # call super
        super().__init__(*vars, **kwargs)

    def set_enabled(self, enabled = True):

        super().set_enabled(enabled)
        
    def read(self):

        #print('> read')
        if self.enabled:

            self.output = self.mpu.getMotion6()
        
        #print('< read')
        return self.output

class IMU(block.Block):

    def __init__(self, *vars, **kwargs):

        # Sensor initialization
        self.mpu = mpu6050.MPU6050()
        self.mpu.dmpInitialize()

        # get expected DMP packet size for later comparison
        self.packetSize = self.mpu.dmpGetFIFOPacketSize() 

        # call super
        super().__init__(*vars, **kwargs)

    def set_enabled(self, enabled = True):

        super().set_enabled(enabled)
        
        if enabled:
            self.mpu.setDMPEnabled(True)
            self.mpu.resetFIFO()
            warnings.warn('> imu enabled')
        else:
            self.mpu.setDMPEnabled(False)
            warnings.warn('> imu disabled')

    def read(self):

        #print('> read')
        if self.enabled:

            # get current FIFO count
            fifoCount = self.mpu.getFIFOCount()
            #print('> fifoCount1 = {}'.format(fifoCount))

            if fifoCount == 1024:
                # reset so we can continue cleanly
                self.mpu.resetFIFO()
                print('FIFO overflow!')
            
            fifoCount = self.mpu.getFIFOCount()
            #print('> fifoCount2 = {}'.format(fifoCount))
            while fifoCount < self.packetSize:
                fifoCount = self.mpu.getFIFOCount()
                #print('> fifoCount3 = {}'.format(fifoCount))

            result = self.mpu.getFIFOBytes(self.packetSize)
            q = self.mpu.dmpGetQuaternion(result)

            self.output = (q['w'], q['x'], q['y'], q['z'])
        
        #print('< read')
        return self.output

class Inclinometer(IMU):

    def read(self):

        # read imu
        (w, x, y, z) = super().read()

        # construct quaternion
        ez = [2*(self.x * self.z + self.y * self.w),
              2*(self.y * self.z - self.x * self.w),
              1 - 2*(self.x * self.x + self.y * self.y)]
        theta = -math.atan2(ez[2], math.sqrt(ez[0]**2+ez[1]**2)) / (2 * math.pi)
        print('\r {} {}'.format(ez, theta), end='')
        
        # from quaternion to vector
        (gx, gy, gz) = (float(2 * (x * z - w * y)),
                        float(2 * (w * x + y * z)),
                        float(w * w - x * x - y * y + z * z))

        # calculate angle
        # TODO: FIX FRAME
        theta = - math.atan2(gz, math.sqrt(gx**2+gy**2)) / (2 * math.pi)

        return (theta, )

if __name__ == "__main__":

    import time, math

    T = 0.04
    K = 1000

    # print("> Testing Raw")
    
    # accel = Raw()

    # k = 0
    # while k < K:

    #     # read accelerometer
    #     (ax, ay, az, gx, gy, gz) = accel.read()

    #     print('\r> (ax, ay, az, gx, gy, gz) = ({:+5.3f}, {:+5.3f}, {:+5.3f}, {:+5.3f}, {:+5.3f}, {:+5.3f})'.format(ax, ay, az, gx, gy, gz), end='')

    #     time.sleep(T)
    #     k += 1

    # print("> Testing accelerometer")
    
    # accel = IMU()

    # k = 0
    # while k < K:

    #     # read accelerometer
    #     (w, x, y, z) = accel.read()

    #     print('\r> (w, x, y, z) = ({:+5.3f}, {:+5.3f}, {:+5.3f}, {:+5.3f})g'.format(w, x, y, z), end='')

    #     time.sleep(T)
    #     k += 1

    print("\n> Testing inclinometer")
    
    accel = Inclinometer()
    print("\n> ")
    accel.set_enabled(enabled = True)

    k = 0
    while True:

        # read inclinometer
        (theta, ) = accel.read()
        #print('\r> theta = {:+05.3f}deg'.format(360*theta), end='')
        
        #time.sleep(T)
        k += 1
