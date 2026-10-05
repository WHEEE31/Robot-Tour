"""
NOT TO BE MODIFIED AT EVENT
DO NOT TOUCH THIS FILE!!!!!
"""

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor, GyroSensor, TouchSensor
from pybricks.parameters import Stop, Color, Button, Port, Direction
from pybricks.robotics import DriveBase

import time
import math

class RobotTour2025():
    def __init__(self, ports_dict, params_dict, times_dict):

        self.r_brick = EV3Brick()
        self.gyro = GyroSensor(ports_dict["gyro"])
        self.color_left = ColorSensor(ports_dict["left color sensor"])
        self.color_right = ColorSensor(ports_dict["right color sensor"])
        self.m_left = Motor(ports_dict["left motor"], positive_direction=Direction.COUNTERCLOCKWISE)
        self.m_right = Motor(ports_dict["right motor"], positive_direction=Direction.COUNTERCLOCKWISE)
        #self.poke = TouchSensor(ports_dict["touch sensor"])

        self.MAX_RPM = params_dict["max rpm"]
        self.WHEEL_CIRCUMFERENCE = params_dict["wheel circumference"]
        self.TRACK = params_dict["robot diameter"]
        self.DOWEL_DIS = params_dict["wheel to dowel"]
        self.GYRO_BUFFER = params_dict["gyro buffer"]
        self.MOVEMENT_BUFFER = params_dict["movement buffer"]

        self.FORWARD_COEF = params_dict["forward padding"]
        self.BACKWARD_COEF = params_dict["backward padding"]
        self.TURN_COEF = params_dict["turn padding"]

        self.driver = DriveBase(left_motor = self.m_left, right_motor = self.m_right, wheel_diameter = self.WHEEL_CIRCUMFERENCE/math.pi * 10, axle_track = self.TRACK * 10)
        self.driver.settings()

        self.T_TURN = times_dict["turn"]
        self.T_ENTER = times_dict["enter"]
        self.T_EXIT = times_dict["exit"]
        self.movementSpeed = 0

        self.running = False
        self.finished = False

        self.commands = []
        self.currentIndex = -1

    def queue(self, target, commands):        
        """
        RobotTour2025.queue(list commands) --> None
        preps robot based on the inputted commands for completing the maze
        """

        self.commands = commands
        amounts = [0,0,0,0] # forward/backward, turns, bumps, gate aligns
        
        for i in range(len(self.commands)):
            self.commands[i] = self.commands[i].upper()
            step = self.commands[i]
            if step in ["FORWARD", "BACKWARD"]:
                amounts[0] += 1
            elif step in ["LEFT", "RIGHT"]:
                amounts[1] += 1
            elif step == "BUMP":
                amounts[2] += 1
            elif step == "GATE ALIGN":
                amounts[3] += 1
        
        distance = amounts[0] * 50 + amounts[2] * (25-self.DOWEL_DIS+3) * 2     # cm
        availableTime = target - self.T_ENTER - self.T_EXIT - (len(self.commands)-1)*self.MOVEMENT_BUFFER - amounts[1]*self.T_TURN - amounts[3]*3 # assume 3 seconds for gate align
        self.movementSpeed = distance / availableTime      # cm / secx
        
    def executeNextCommand(self):
        self.currentIndex += 1
        if self.currentIndex >= len(self.commands):
            self.finished = True
            return
        self.running = True
        command = self.commands[self.currentIndex]
        if command == "FORWARD":
            self.forward()
        elif command == "BACKWARD":
            self.backward()
        elif command == "LEFT":
            self.turnLeft()
        elif command == "RIGHT":
            self.turnRight()
        elif command == "BUMP":
            self.bump()
        elif command == "GATE ALIGN":
            self.gateAlign()
        elif command == 'ENTER':
            self.enter()
        elif command == 'EXIT':
            self.exit()
    
    def forward(self, distance=50, time = 0):
        #print('executing [forward]')
        if (time == 0):
            movementSpeed = self.movementSpeed
        else:
            movementSpeed = distance / time

        movementSpeed_mm = movementSpeed * 10
        distance_mm = distance * 10
        self.driver.stop(Stop.COAST)
        self.driver.settings(straight_speed=movementSpeed_mm * self.FORWARD_COEF, straight_acceleration = 1500)
        self.driver.straight(distance = distance_mm)

        self.driver.stop(Stop.BRAKE)

    def backward(self, distance=50, time = 0):
        #print('executing [forward]')
        self.forward(-distance, time)

    def turnRight(self, angle = 90):
        #print('executing [turnRight]')
        #self.driver.turn(90)
        #self.driver.stop(Stop.HOLD)

        self.driver.stop(Stop.COAST)
        self.driver.drive(0, angle/(self.T_TURN * self.TURN_COEF))
        #### gyro method
        self.gyro.reset_angle(0)
        #while abs(self.gyro.angle()) < abs(angle) + self.GYRO_BUFFER:
        #    print(str(self.gyro.angle()) + " " + str(self.driver.angle()), end = '     \n')
        #    time.sleep(0.005)
        #### wheelbase method
        #self.driver.reset()
        #while abs(self.driver.angle()) < abs(angle) + self.GYRO_BUFFER:
        #    print(str(self.gyro.angle()) + " " + str(self.driver.angle()), end = '     \n')
        #print('done' + str(self.gyro.angle()) + " " + str(self.driver.angle()), end = '     \n')
        #### timing method
        start_time = time.time()
        while time.time() - start_time < 5:
            print(str(self.gyro.angle()))
        self.driver.stop(Stop.BRAKE)
        print(self.gyro.angle())
        self.gyro.reset_angle(0)

    def turnLeft(self):
        #print('executing [turnLeft]')
        self.turnRight(-90)

    def enter(self):
        #print('executing [enter]')
        self.forward(self.DOWEL_DIS-25, self.T_ENTER)

    def exit(self):
        #print('executing [exit]')     
        self.forward(-self.DOWEL_DIS, self.T_EXIT)

    ## more specialized commands ##

    def gateAlign(self):
        pass

    def bump(self):
        #print('executing [bump]')
        self.forward(25-self.DOWEL_DIS+3)
        self.forward(-25+self.DOWEL_DIS-3)

class EventHandler():
    def __init__(self):
        self.robot = None
        self.absoluteTime = 0
        self.runningTime = 0
        self.started = False
        self.paused = False

    def update(self, r):
        self.robot = r
        '''
        # self.absoluteTime is updated by the timer thread in __main__
        if self.robot.running:
            self.runningTime += self.INCREMENT
        '''

        # check touch sensor and update started and paused
        if Button.CENTER in self.robot.r_brick.buttons.pressed():
            if not self.started:
                self.robot.r_brick.screen.clear()
                self.robot.r_brick.screen.draw_text(10,10, "Starting!")
                time.sleep(1)
                self.started = True
            else:
                pass
                #self.paused = not self.paused
            
        if self.isFinished():
            print("\nFinished touring!")
            self.robot.driver.stop(Stop.HOLD)
            self.robot.r_brick.screen.clear()
            self.robot.r_brick.screen.draw_text(10,10, "Time: " + self.getDisplayTime(self.runningTime))
            self.robot.r_brick.screen.draw_text(10,30, "All " + str(len(self.robot.commands)) +" actions")
            self.robot.r_brick.screen.draw_text(10,50, "completed!")

    def updateScreen(self):
        if not self.isFinished():
            self.robot.r_brick.screen.clear()
            self.robot.r_brick.screen.draw_text(10,10, "Time: " + self.getDisplayTime(self.runningTime))
            if not self.isPaused():
                self.robot.r_brick.screen.draw_text(10,30, "Now: " + str(self.robot.commands[self.robot.currentIndex]))
                self.robot.r_brick.screen.draw_text(10,50, "Action " + str(self.robot.currentIndex+1) + "/" + str(len(self.robot.commands)))
            else:
                self.robot.r_brick.screen.draw_text(10,40, "PAUSED!")
        
    def updateLog(self):
        #print("Brick states: " + self.robot.driver.state()[0] + "," + self.robot.driver.state()[1] + "," + self.robot.driver.state()[2] + "," + self.robot.driver.state()[3])
        print(" Program runtime: " + str(self.absoluteTime) + " Robot runtime: " + str(self.runningTime) + " | Current action (" + str(self.robot.currentIndex + 1) + "): " + ("finished" if self.isFinished() else self.robot.commands[self.robot.currentIndex]), end = '       \r')

    def isRunning(self):
        # return (self.robot.r_brick.state()[1] > 0 or self.robot.r_brick.state()[3] > 0)
        return self.robot.running

    def isFinished(self):
        # return (self.robot.current)
        return self.robot.finished
    
    def isStarted(self):
        # check if touch sensor is depressed
        return self.started
    
    def isPaused(self):
        # check if touch sensor is depressed
        return self.paused
    
    def getDisplayTime(self, time):
        displayTime = ""
        sec = "{:.2f}".format(time)
        if time > 60:
            min = time // 60
            sec = time - 60 * min
            if len(str(min)) == 1:
                displayTime += "0"
            displayTime += str(min)
        else:
            displayTime += "00"
        displayTime += ":"
        if len(str(sec)) == 1:
            displayTime += "0"
        displayTime += str(sec)

        return displayTime
