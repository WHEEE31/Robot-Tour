#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor, GyroSensor, TouchSensor
from pybricks.iodevices import UARTDevice#, I2CDevice
from pybricks.parameters import Stop, Color, Button, Port, Direction
from pybricks.robotics import DriveBase
from pybricks.tools import wait

import time
import math
import sys
import random

""" ******************************************
                  edit this!
****************************************** """
targetTime = 58
queue = ['ENTER',
         'LEFT',
         'FORWARD',
         'RIGHT',
         'FORWARD2',
         'LEFT',
         'LEFT',
         'FORWARD2',
         'LEFT',
         'FORWARD',
         'LEFT',
         'FORWARD3',
         'MINIBUMP',
         'LEFT',
         'FORWARD3',
         'LEFT',
         'FORWARD2',
         'RIGHT',
         'FORWARD',
         'RIGHT',
         'FORWARD',
         'LEFT',
         'LEFT',
         'BACKBUMP',
         'FORWARD2',
         'LEFT',
         'FORWARD',
         'LEFT',
         'LEFT',
         'BACKBUMP',
         'RIGHT',
         'FORWARD',
         'EXIT']

""" ******************************************
                  backend
****************************************** """
class Odometry:
    def __init__(self):
        self.x = 0.0        # mm, world frame
        self.y = 0.0        # mm, world frame
        self._last_dist = 0
    
    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self._last_dist = r_driver.distance()
    
    def update(self):
        current_dist = r_driver.distance()
        delta = current_dist - self._last_dist
        self._last_dist = current_dist
        
        heading_rad = math.radians(r_gyro.angle())
        self.x += delta * math.sin(heading_rad)
        self.y += delta * math.cos(heading_rad)
    
    def get_grid_center_offset(self, grid_mm=500):
        """Returns (dx, dy) in world frame from current pos to nearest grid center"""
        center_x = round(self.x / grid_mm) * grid_mm
        center_y = round(self.y / grid_mm) * grid_mm
        return center_x - self.x, center_y - self.y
    
    def get_robot_frame_correction(self, grid_mm=500):
        """
        Returns (forward_mm, lateral_mm) correction in robot's local frame.
        Forward = along robot heading, lateral = perpendicular (+ = left)
        """
        dx, dy = self.get_grid_center_offset(grid_mm)
        
        heading_rad = math.radians(r_gyro.angle())
        
        # Project world offset into robot frame
        forward = dx * math.sin(heading_rad) + dy * math.cos(heading_rad)
        lateral = dx * math.cos(heading_rad) - dy * math.sin(heading_rad)
        
        return forward, lateral

### gyro
class ArduinoGyro:
    def __init__(self, port, test=False):
        self.test = test
        if test:
            self.gyro = GyroSensor(ports["old gyro"])
        else:
            self.gyro = UARTDevice(port, 115200)

        self.lastValidHeading = 0.0

    def reset(self):
        self.gyro.read_all() 
        self.gyro.write(b'r')

    def calibrate(self, samples=None):
        self.gyro.read_all() 
        if samples is None:
            self.gyro.write(b'c')
        else:
            command = "c" + str(samples)
            self.gyro.write(command.encode())
        while True:
            if self.is_calibrating():
                print('still calibrating', end='\r')
            else:
                print('done!')
                return
            time.sleep(5)

    def is_calibrating(self):
        self.gyro.read_all() 
        self.gyro.write(b'i')

        start = time.ticks_ms()
        while self.gyro.waiting() == 0:
            if time.ticks_diff(time.ticks_ms(), start) > 3000:
                return "Timeout"
        line = self.gyro.read_all().decode().strip()
        return line == "1"
    
    def angle(self):
        if self.test:
            return self.gyro.angle()
        
        h = self.get_heading()
        if isinstance(h, float):
            return int(h)
        return self.lastValidHeading

    def get_heading(self):
        self.gyro.read_all() 
        
        self.gyro.write(b'h')
        
        # Wait for the Arduino to send the line back (timeout after 50ms)
        start = time.ticks_ms()
        while self.gyro.waiting() == 0:
            if time.ticks_diff(time.ticks_ms(), start) > 1000:
                return "Timeout"
        
        try:
            data = self.gyro.read_all().decode().strip()
            heading = float(data)
            
            if heading == 777:
                return self.lastValidHeading
            
            self.lastValidHeading = heading
            return heading
        except (ValueError, OSError):
            return self.lastValidHeading
        
    def get_displaced_angle(self, current, start):
        """Calculates the absolute distance traveled from start, 
        handling potential 360-degree wrap-around."""
        diff = current - start

        while diff > 180: diff -= 360
        while diff < -180: diff += 360
        return diff
    
    def get_snap_angle(self):
        """Returns the nearest 90-degree increment to the current heading."""
        # Use the cumulative angle to determine which grid line we are on
        current = self.angle()
        return round(current / 90) * 90

### movement functions
def forward(distance = 50, duration = 0):
    """
        forward(distance = 50, duration = 0) --> None
        Moves the robot forward by distance cm in duration sec
        duration set to calculated time if not specified here
    """
    direction = -1 if distance < 0 else 1
    ramped = False
    if duration == 0:
        movementSpeed = r_movementSpeed * direction
        ramped = True
    else:
        movementSpeed = distance / duration
    s = movementSpeed * 10 * times["move offset"]
    d = distance * 10 * (params["ramp buffer"] if ramped else params["move buffer"])

    start_d = r_driver.distance()
    target_h = r_gyro.get_snap_angle() #r_gyro.angle()
    print('forward target heading is ' + str(target_h))
    inramp_dist = 40
    outramp_dist = 60
    
    while abs(r_driver.distance()-start_d) < abs(d):
        r_odo.update()
        current_h = r_gyro.angle()
        error = r_gyro.get_displaced_angle(target_h, current_h)

        print('driving at heading with error::' + str(current_h) + ', ' + str(error))

        gain = 3.5
        correction = error * gain

        if ramped:
            travelled = abs(r_driver.distance() - start_d)
            remaining = abs(d) - travelled
            ramp_in = abs(min(travelled / inramp_dist, 1.0)) ** (1/2)
            ramp_out = abs(min(remaining / outramp_dist, 1.0)) ** (1/2)
            ramp = min(ramp_in, ramp_out)
            speed_factor = min(ramp,1)
            speed = s*max(speed_factor,0.5)
            r_driver.drive(speed*1.1, correction)
        else:
            r_driver.drive(s, correction)

    r_driver.stop(Stop.BRAKE)

def forward2():
    forward(100)

def forward3():
    forward(150)

def forward4():
    forward(200)

def backward(distance = 50, duration = 0):
    """
    backward(distance = 50, duration = 0) --> None
        Moves the robot backward by distance cm in duration sec
        duration set to calculated time if not specified here
    """
    forward(-1 * distance, duration)

def bump():
    """
    bump() --> None
        Performs a bump maneuver on the robot
        forward to enter dowel, then back to center position
        time derived from calculated speed
    """
    forward(25 + params["wheel to dowel"] + 5)
    backward(25 + params["wheel to dowel"] + 5)

def minibump():
    """
    minibump
    """

    forward(7, times["minibump"]/2)
    backward(7, times["minibump"]/2)

def backbump():
    backward(25 - params["wheel to dowel"] + 5)
    forward(25 - params["wheel to dowel"] + 5)

def enter():
    r_gyro.reset()
    forward(25 - params["wheel to dowel"], times["enter"])

def exit():
    forward(params["wheel to dowel"], times["exit"])
    '''
    forward_correction, lateral_correction = r_odo.get_robot_frame_correction()
    
    distance = math.sqrt(forward_correction**2 + lateral_correction**2)
    angle_to_target = math.degrees(math.atan2(lateral_correction, forward_correction))
    
    print("exit - turn: " + str(round(angle_to_target, 1)) + 
          "deg  drive: " + str(round(distance)) + "mm")
    
    if distance < 5:
        print("Already centered, skipping")
        return
    
    # Turn to face grid center
    if abs(angle_to_target) > 2:
        if angle_to_target > 0:
            left(angle_to_target, snap=False)
        else:
            right(-angle_to_target, snap=False)
    
    # Drive dowel to grid center
    forward(distance / 10)
    '''

def left(angle = 90, snap=True):
    r_driver.stop(Stop.BRAKE)
    r_driver.settings(0,0,0,2)

    startHeading = r_gyro.angle()
    targetHeading = abs(angle) - (params["gyro buffer"] if abs(angle) == 90 else 0)
    r_driver.drive(0, angle / times["turn"] * times["turn offset"])

    #print("DEBUG: Start:", startHeading, "Target Threshold:", startHeading+angle)

    while True:
        r_odo.update()
        current = r_gyro.angle()
        traversed = abs(r_gyro.get_displaced_angle(current, startHeading))

        if traversed >= targetHeading:
            break
        time.sleep(0.001)
    r_driver.stop(Stop.BRAKE)
    print("done: started at " + str(startHeading) + ", commanded +" + str(angle) + ", final is " + str(r_gyro.angle()))
    time.sleep(0.05)
    start_h = r_gyro.angle()
    target_h = r_gyro.get_snap_angle() if snap else start_h
    print("try: " + str(start_h) + " to " + str(target_h))
    r_driver.drive(0, 15*(1 if start_h<target_h else -1))
    while True:
        current = r_gyro.angle()
        traversed = abs(r_gyro.get_displaced_angle(current, start_h))
        if traversed >= abs(r_gyro.get_displaced_angle(target_h, start_h)):
            break
        time.sleep(0.001)
    print("done: computer thinks gyro angle is " + str(r_gyro.angle()))
    r_driver.stop(Stop.BRAKE)

def right(angle = 90, snap = True):
    left(-1 * angle, snap)

## outdated function content
def raise_arm():
    r_driver.stop(Stop.BRAKE)
    r_arm.run_angle(speed=(params["arm angle"]/times["arm"]), rotation_angle=-1*params["arm angle"])

def lower_arm():
    r_driver.stop(Stop.BRAKE)
    r_arm.run_angle(speed=(params["arm angle"]/times["arm"]), rotation_angle=params["arm angle"])

def align():
    r_driver.drive(params["align speed"]*2 ,0)
    found = -1

    while (found == -1):
        for i, sensor in enumerate([r_color_left, r_color_right]):
            if (sensor.reflection() < params["color ground"] - params["color threshold"] 
                or sensor.reflection() > params["color ground"] + params["color threshold"]):
                found = i
                break
    r_driver.stop(Stop.BRAKE)
    print("Color Sensor " + str(found) + " found line first.")
    
    motor_to_run = [r_motor_right, r_motor_left][found]
    sensor_to_check = [r_color_right, r_color_left][found]

    motor_to_run.reset_angle(0)
    motor_to_run.run(params["align speed"])

    while True:
        if (sensor_to_check.reflection() < params["color ground"] - params["color threshold"] or
            sensor_to_check.reflection() > params["color ground"] + params["color threshold"]):
            break
    motor_to_run.stop()
    
    angle_turned = motor_to_run.angle()
    print("Measured correction angle:", angle_turned)
    motor_to_run.run_angle(params["align speed"], angle_turned*2, wait=True)

    forward(25+params["wheel to dowel"], 3)
    
### misc functions
def initQueue(targetTime, queue):
    r_movementSpeed = 0; r_commands = []

    counts = [0,0,0,0,0,0,0,0,0]    # forward/backward, bump, minibump, backbump, enter, exit, left/right, raise/lower, align
    for step in queue:
        if step == "FORWARD":
            counts[0] += 1
            r_commands.append(forward)
        elif step == "FORWARD2":
            counts[0] += 2
            r_commands.append(forward2)
        elif step == "FORWARD3":
            counts[0] += 3
            r_commands.append(forward3)
        elif step == "FORWARD4":
            counts[0] += 4
            r_commands.append(forward4)
        elif step == "BACKWARD":
            counts[0] += 1
            r_commands.append(backward)
        elif step == "BUMP":
            counts[1] += 1
            r_commands.append(bump)
        elif step == "MINIBUMP":
            counts[2] += 1
            r_commands.append(minibump)
        elif step == "BACKBUMP":
            counts[3] += 1
            r_commands.append(backbump)

        elif step == "ENTER":
            counts[4] += 1
            r_commands.append(enter)
        elif step == "EXIT":
            counts[5] += 1
            r_commands.append(exit)

        elif step == "LEFT":
            counts[6] += 1
            r_commands.append(left)
        elif step == "RIGHT":
            counts[6] += 1
            r_commands.append(right)

        elif step == "RAISE":
            counts[7] += 1
        elif step == "LOWER":
            counts[8] += 1
        elif step == "ALIGN":
            counts[9] += 1
        elif step == "CALIBRATE":
            pass

    r_movementSpeed = (
        (
            counts[0]*50 + counts[1]*(25+params["wheel to dowel"]+params["bump buffer"])*2 + 
            counts[2]*(params["minibump size"])*2 + counts[3]*(25-params["wheel to dowel"]+params["backbump buffer"])*2
        ) /
        abs(
            targetTime - counts[4]*times["enter"] - counts[5]*times["exit"] - counts[8]*times["align"]- 
            (len(r_commands)-1)*times["movement buffer"] - counts[2] * times["minibump"] - 
            counts[6]*times["avg turn"] - counts[7]*times["arm"]
        )
    )
    print(r_movementSpeed)
    return r_movementSpeed, r_commands

def blit(text, anchor_coords=[10, 10], spacing=20, tab_width=4):
    r_brick.screen.clear()
    
    text = text.replace('\t', ' ' * tab_width)
    
    processed_text = []
    for char in text:
        if char == '\b':
            if processed_text:
                processed_text.pop()
        else:
            processed_text.append(char)
    text = ''.join(processed_text)
    
    lines = []
    for line in text.split('\n'):
        segments = line.split('\r')
        lines.append(segments[-1])
    
    final_lines = []
    for line in lines:
        segments = line.split('\v')
        for i, segment in enumerate(segments):
            final_lines.append(segment)
            if i < len(segments) - 1:
                final_lines.append('')
    
    y = anchor_coords[1]
    for line in final_lines:
        r_brick.screen.draw_text(anchor_coords[0], y, line)
        y += spacing
    
    print(text)

### specs
ports = {"gyro" : Port.S4,
         "old gyro" : Port.S1,
         "left color sensor" : Port.S2,
         "right color sensor" : Port.S3,
         "touch sensor" : Port.S2,
         "left motor" : Port.B,  
         "right motor" : Port.C,
         "arm motor" : Port.A}  

params = {"max rpm" : 190,                      # 
          "wheel circumference" : 19.62,        # cm
          "robot diameter" : 14.45,             # cm
          "wheel to dowel" : 13.69,             # cm

          "gyro buffer" : 16,                   # degrees           larger = robot will turn less degrees       10!!!
          "move buffer" : 1.006,                # coef              larger = robot will move farther
          "ramp buffer" : 1.02,
          "bump buffer" : 5,                    # cm                larger = robot moves more
          "backbump buffer" : 5,                # cm
          "minibump size" : 7,                  # cm

          "color ground" : 5,                   # percentage
          "color threshold" : 3,
          "align speed" : 70,
          "arm angle" : 270}

times = {"turn" : 0.6,                          # sec   (coarse turn)
         "avg turn" : 1.02,                      # sec   (coarse + refinement)
         "enter" : 0.7,                         # sec
         "exit" : 0.7,                          # sec
         "minibump" : 0.8,

         "align" : 5,                           
         "arm" : 0.5,
         "movement buffer" : 0.01,              # sec               larger = longer pauses between actions
         "turn offset" : 1.06,                  # coef              larger = faster movement
         "move offset" : 1.06,                  # coefs
         "start time" : 3}

### robot init
r_brick = EV3Brick()
r_gyro = ArduinoGyro(ports["gyro"])
r_odo = Odometry()

r_motor_left = Motor(ports["left motor"], positive_direction = Direction.CLOCKWISE)
r_motor_right = Motor(ports["right motor"], positive_direction = Direction.CLOCKWISE)
#r_arm = Motor(ports["arm motor"], positive_direction = Direction.CLOCKWISE)
#r_color_left = ColorSensor(ports["left color sensor"])
#r_color_right = ColorSensor(ports["right color sensor"])
#r_touch = TouchSensor(ports["touch sensor"])
r_driver = DriveBase(left_motor = r_motor_left, 
                     right_motor = r_motor_right, 
                     wheel_diameter = params["wheel circumference"] / math.pi * 10, 
                     axle_track = params["robot diameter"] * 10)
r_movementSpeed, r_commands = initQueue(targetTime, queue)

print("Init completed!\n  Movement speed: " + str(r_movementSpeed) + "\n  # commands: " + str(len(r_commands)))

### main

for i in range(times["start time"]):
    blit("Starting... " + str(times["start time"]-i))
    time.sleep(1)

start_time = time.perf_counter()
r_gyro.reset()

for i, callable in enumerate(r_commands):
    blit("Current step: " + str(queue[i]) + "\n  Step " + str(i+1) + " / " + str(len(r_commands)) + "\n  Elapsed time: " + str(time.perf_counter() - start_time))
    callable()
    if (i < len(r_commands)-1):
        time.sleep(times["movement buffer"])

end_time = time.perf_counter()
blit("Finished! \nt: " + str(end_time - start_time))
time.sleep(100)
sys.exit()

#blessed by Jemil, good luck <3