
from pybricks.ev3devices import Motor
from pybricks.parameters import Port, Button
from pybricks.hubs import EV3Brick
from pybricks.tools import wait

# Initialize the EV3 Brick and the Motor
ev3 = EV3Brick()
motor_a = Motor(Port.A)

# Define the speed (degrees per second)
SPEED = 500

print("Control active: Use Left/Right buttons. Center to exit.")

while True:
    print(motor_a.angle(), end = '\r')
    # Check which buttons are pressed
    pressed = ev3.buttons.pressed()

    if Button.LEFT in pressed:
        motor_a.run(-SPEED)
    elif Button.RIGHT in pressed:
        motor_a.run(SPEED)
    elif Button.CENTER in pressed:
        # Stop the program if the center button is pressed
        motor_a.stop()
        break
    else:
        # Stop the motor if no direction buttons are held
        motor_a.stop()

    # Small delay to keep the loop smooth
    wait(10)