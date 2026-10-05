

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor, GyroSensor, TouchSensor
from pybricks.parameters import Stop, Color, Button, Port, Direction
from pybricks.robotics import DriveBase

import sys
import time
import utils
import threading

""" ******************************************
    all data structures and variables here
****************************************** """

ports = {"gyro" : Port.S1,
         "left color sensor" : Port.S3,
         "right color sensor" : Port.S4,
         "touch sensor" : Port.S2,
         "left motor" : Port.B,  
         "right motor" : Port.C}  

params = {"max rpm" : 190,                      # 
          "wheel circumference" : 19.62,        # cm
          "robot diameter" : 14.45,             # cm
          "wheel to dowel" : 13.69,             # cm
          "gyro buffer" : -22,                  # degrees
          "movement buffer" : 0,                # seconds
          "forward padding" : 1,
          "backward padding" : 1,
          "turn padding" : 0.63}

times = {"turn" : 2,                            # seconds
         "enter" : 1,                         # seconds
         "exit" : 1}                          # seconds

targetTime = 66
x = 2
if x == 1:
    queue = ['LEFT' for _ in range(4)]
elif x == 0:
    queue = ['RIGHT' for _ in range(4)]
elif x == 2:
    queue = ['LEFT']
elif x == 3:
    queue = ['RIGHT']
elif x == 4:
    queue = ['ENTER',
             'EXIT']
elif x == 5:
    queue = ['FORWARD']
elif x == 6:
    queue = ['BACKWARD']

def tourer_thread():
    while not tourer.finished:
        if not eventHandler.isPaused():
            tourer.executeNextCommand()
        time.sleep(tourer.MOVEMENT_BUFFER)

def eventHandler_thread():
    while not eventHandler.isFinished():
        eventHandler.update(tourer)
        #eventHandler.updateLog()
        eventHandler.updateScreen()

def timing_thread():
    start_time = time.perf_counter()
    while True:
        current_time = time.perf_counter()
        eventHandler.absoluteTime = current_time - start_time
        time.sleep(0.005)  # Minimize CPU usage

def runtime_thread():
    while not eventHandler.isStarted():
        time.sleep(0.01)  # Wait for the start signal

    start_time = time.perf_counter()
    while True:
        current_time = time.perf_counter()
        eventHandler.runningTime = current_time - start_time
        time.sleep(0.005)  # Minimize CPU usage

tourer = utils.RobotTour2025(ports, params, times)
eventHandler = utils.EventHandler()

touring = threading.Thread(target = tourer_thread)
eventHandling = threading.Thread(target = eventHandler_thread)
timing = threading.Thread(target = timing_thread)
running = threading.Thread(target = runtime_thread)

""" ******************************************
              start the program!
****************************************** """
"""
    THIS IS WHERE YOU INPUT THE LIST OF COMMANDS 
     --> SHOULD BE "FORWARD" "BACKWARD" "LEFT" "RIGHT" "BUMP" "GATE ALIGN"
     --> SHOULD START WITH "ENTER" AND END WITH "EXIT"
"""
# paste back here
'''
targetTime = 70
queue = ["ENTER",
         "RIGHT",
         "RIGHT",
         "FORWARD",
         "FORWARD",
         "FORWARD",
         "RIGHT",
         "FORWARD",
         "LEFT",
         "FORWARD",
         "LEFT",
         "BUMP",
         "LEFT",
         "FORWARD",
         "RIGHT",
         "FORWARD",
         "LEFT",
         "FORWARD",
         "FORWARD",
         "LEFT",
         "FORWARD",
         "LEFT",
         "BUMP",
         "RIGHT",
         "FORWARD",
         "RIGHT",
         "FORWARD",
         "RIGHT",
         "BUMP",
         "RIGHT",
         "FORWARD",
         "RIGHT",
         "FORWARD",
         "RIGHT",
         "BUMP",
         "RIGHT",
         "RIGHT",
         "FORWARD",
         "LEFT",
         "FORWARD",
         "RIGHT",
         "FORWARD",
         "EXIT"]
'''
tourer.queue(targetTime, queue)

tourer.r_brick.screen.clear()
tourer.r_brick.screen.draw_text(10,10, "press center")
print("press center")

# wait for start signal        
timing.start()    
while not eventHandler.isStarted():
    eventHandler.update(tourer)

# start threads
#running.start()
#touring.start()
#eventHandling.start()

# break once finished
    """
if __name__ == "__main__":
    while True:
        if (eventHandler.isFinished()):
            print('\n')
            time.sleep(10)
            break
"""

tourer.executeNextCommand()
sys.exit()

