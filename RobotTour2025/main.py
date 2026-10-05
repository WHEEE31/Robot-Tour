#!/usr/bin/env pybricks-micropython

from pybricks.parameters import Port
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor, GyroSensor, TouchSensor
from pybricks.parameters import Stop, Color, Button, Port, Direction
from pybricks.robotics import DriveBase
from pybricks.tools import wait

import time
import math
import sys

""" ******************************************
                  edit this!
****************************************** """

targetTime = 0

queue = [        "ENTER",
        "RIGHT",
        "FORWARD",
        "FORWARD",
        "LEFT",
        "FORWARD",
        "FORWARD",
        "FORWARD",
        "RIGHT",
        "LEFT",
        "BUMP",
        "EXIT"]

""" ******************************************
                  backend
****************************************** """

### movement functions
def forward(distance = 50, duration = 0):
    """
    forward(distance = 50, duration = 0) --> None
        Moves the robot forward by distance cm in duration sec
        duration set to calculated time if not specified here
    """
    if duration == 0:
        movementSpeed = r_movementSpeed
    else:
        movementSpeed = distance / duration
    movementSpeed *= 10; distance *= 10

    r_driver.stop(Stop.BRAKE)
    r_driver.settings(straight_speed = movementSpeed * times["move offset"], straight_acceleration = 1500)
    r_driver.straight(distance = distance * params["move buffer"])
    r_driver.stop(Stop.BRAKE)

def backward(distance = 50, duration = 0):
    """
    backward(distance = 50, duration = 0) --> None
        Moves the robot backward by distance cm in duration sec
        duration set to calculated time if not specified here
    """
    forward(-1 * distance, duration)

def left(angle = 90):
    """
    left(angle = 90) --> None
        Turns the robot angle degrees towards its right
        at a speed set in the times{} dict
    """
    r_driver.stop(Stop.BRAKE)
    r_gyro.reset_angle(0)
    r_driver.settings(0,0,0,2)
    r_driver.drive(0, angle / times["turn"] * times["turn offset"])
    while abs(r_gyro.angle()) < abs(angle) + params["gyro buffer"]:
        pass
    r_driver.stop(Stop.BRAKE)
    print("done: computer thinks gyro angle is " + str(r_gyro.angle()))

    r_gyro.reset_angle(0)

def right(angle = 90):
    """
    right(angle = 90) --> Non+e
        Turns the robot angle degrees towards its left
        at a speed set in the times{} dict
    """ 
    left(-1 * angle)

def bump():
    """
    bump() --> None
        Performs a bump maneuver on the robot
        forward to enter dowel, then back to center position
        time derived from calculated speed
    """
    forward(25 - params["wheel to dowel"] + 10)
    backward(25 - params["wheel to dowel"] + 10)

def enter():
    """
    enter() --> None
        Performs the enter maneuver on the robot
        Dowel at start point to wheel base at center position
        time derived from times{} dict
    """
    backward(params["wheel to dowel"] - 25, times["enter"])

def exit():
    """
    exit() --> None
        Performs the exit maneuver on the robot
        Wheel base at center position to dowel at end point
        time derived from times{} dict
    """
    forward(params["wheel to dowel"], times["exit"])

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
    """
    initQueue(targetTime, queue) --> tuple(double, list)
        Calculates the movementSpeed and commands (callables) based on
        targetTime seconds and queue[] list from gridding
        Returns (movementSpeed, commands)
    """
    r_movementSpeed = 0; r_commands = []

    counts = [0,0,0,0,0,0]    # forward/backward, turn, bump, enter, exit, align
    for step in queue:
        if step == "FORWARD":
            r_commands.append(forward)
            counts[0] += 1
        elif step == "BACKWARD":
            r_commands.append(backward)
            counts[0] += 1
        elif step == "LEFT":
            r_commands.append(left)
            counts[1] += 1
        elif step == "RIGHT":
            r_commands.append(right)
            counts[1] += 1
        elif step == "BUMP":
            r_commands.append(bump)
            counts[2] += 1
        elif step == "ENTER":
            r_commands.append(enter)
            counts[3] += 1
        elif step == "EXIT":
            r_commands.append(exit)
            counts[4] += 1
        elif step == "ALIGN":
            r_commands.append(align)
            counts[5] += 1
    
    r_movementSpeed = (
        (counts[0] * 50 + counts[2] * (25 - params["wheel to dowel"] + 3) * 2) /
        (
            targetTime - times["enter"] * counts[3] - times["exit"] * counts[4] - times["align"] * counts[5] - 
            (len(r_commands) - 1) * times["movement buffer"] - (counts[0] - 1) * times["mb"] - 
            counts[1] * times["turn"]
        )
    )

    return r_movementSpeed, r_commands

def blit(text, anchor_coords=[10, 10], spacing=20, tab_width=4):
    """
    blit(text, anchor_coords=[10, 10], spacing=20, tab_width=4) --> None
        Prints text to the brick's display with specs: anchor_coords, spacing, and tab_width.
        Also prints to terminal.
        
    Parameters:
        text (str): The text to display. Can include special characters like `\n`, `\t`, `\r`, `\b`, and `\v`.
        anchor_coords (list): The [x, y] coordinates for the starting position of the text.
        spacing (int): The vertical spacing between lines of text.
        tab_width (int): The number of spaces to replace each tab character (`\t`).
    """
    # Clear the screen before drawing new text
    r_brick.screen.clear()
    
    # Handle tab characters
    text = text.replace('\t', ' ' * tab_width)
    
    # Handle backspace characters
    processed_text = []
    for char in text:
        if char == '\b':
            if processed_text:
                processed_text.pop()
        else:
            processed_text.append(char)
    text = ''.join(processed_text)
    
    # Handle carriage return characters
    lines = []
    for line in text.split('\n'):
        segments = line.split('\r')
        lines.append(segments[-1])
    
    # Handle vertical tab characters
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
ports = {"gyro" : Port.S1,
         "left color sensor" : Port.S2,
         "right color sensor" : Port.S3,
         "touch sensor" : Port.S2,
         "left motor" : Port.B,  
         "right motor" : Port.C}  

params = {"max rpm" : 190,                      # 
          "wheel circumference" : 19.62,        # cm
          "robot diameter" : 14.45,             # cm
          "wheel to dowel" : 13.69,             # cm
          "gyro buffer" : -7.0,                  # degrees (-5.5)   larger = robot will turn more to the right
          "move buffer" : 1.008,                    #                 larger = robot will move farther
          "color ground" : 5,                    # percentage
          "color threshold" : 3,
          "align speed" : 70}

times = {"turn" : 1.2,                            # seconds
         "enter" : 0.7,                         # seconds
         "exit" : 1.2,                          # seconds
         "align" : 5,
         "movement buffer" : 0.01,                 # seconds
         "turn offset" : 1.055,                     # larger = faster
         "move offset" : 1.035,                      # larger = faster
         "mb" : 0.4}

### robot init
r_brick = EV3Brick()
r_gyro = GyroSensor(ports["gyro"])
r_motor_left = Motor(ports["left motor"], positive_direction = Direction.CLOCKWISE)
r_motor_right = Motor(ports["right motor"], positive_direction = Direction.CLOCKWISE)
r_color_left = ColorSensor(ports["left color sensor"])
r_color_right = ColorSensor(ports["right color sensor"])
#r_touch = TouchSensor(ports["touch sensor"])
r_driver = DriveBase(left_motor = r_motor_left, 
                     right_motor = r_motor_right, 
                     wheel_diameter = params["wheel circumference"] / math.pi * 10, 
                     axle_track = params["robot diameter"] * 10)
r_movementSpeed, r_commands = initQueue(targetTime, queue)

print("Init completed!\n  Movement speed: " + str(r_movementSpeed) + "\n  # commands: " + str(len(r_commands)))

### main

blit("Starting...")
time.sleep(1)
start_time = time.perf_counter()

for i, callable in enumerate(r_commands):
    blit("Current step: " + str(queue[i]) + "\n  Step " + str(i+1) + " / " + str(len(r_commands)) + "\n  Elapsed time: " + str(time.perf_counter() - start_time))
    callable()
    if (i < len(r_commands)-1):
        time.sleep(times["movement buffer"])

end_time = time.perf_counter()
blit("Finished! \nElapsed time: " + str(end_time - start_time))
sys.exit()

