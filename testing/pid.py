import time
import matplotlib.pyplot as plt
'''
class PIDController:
    def __init__(self, Kp, Ki, Kd, setpoint):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.previous_error = 0
        self.integral_sum = 0
        self.last_time = time.time()

    def update(self, current_value):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        error = self.setpoint - current_value

        p_term = self.Kp * error

        self.integral_sum += error * dt
        i_term = self.Ki * self.integral_sum

        derivative_error = (error - self.previous_error) / dt
        d_term = self.Kd * derivative_error

        self.previous_error = error

        output = p_term + i_term + d_term
        return output

# Example usage in a simulation
pid = PIDController(Kp=2.0, Ki=1, Kd=0.4, setpoint=10.0)
current_value = 0
for _ in range(10000):
    time.sleep(0.1)
    control_output = pid.update(current_value)
    current_value += control_output * 0.1 # Simulate system response
    # Plot or log current_value
    print(current_value, end = '\r')
'''

import time

class PIDController:
    def __init__(self, Kp, Ki, Kd, setpoint):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.previous_error = 0
        self.integral_sum = 0
        self.last_time = time.time()

    def update(self, current_value):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        error = self.setpoint - current_value
        self.integral_sum += error * dt
        derivative_error = (error - self.previous_error) / dt if dt > 0 else 0

        self.previous_error = error

        p_term = self.Kp * error
        i_term = self.Ki * self.integral_sum
        d_term = self.Kd * derivative_error

        return p_term + i_term + d_term

# === Simulation Settings ===
MAX_SPEED = 2.0  # max motor speed (units per second)
SETPOINT = 10.0
INITIAL_POSITION = 0.0

# === Initialize PID and state ===
pid = PIDController(Kp=0.8, Ki=0, Kd=0.5, setpoint=SETPOINT)
position = INITIAL_POSITION

# === Simulate over time ===
print("time\tpos\t\tpower\t\terror")
start_time = time.time()

for _ in range(1000):  # simulate ~20 seconds
    now = time.time()
    error = SETPOINT - position
    power = pid.update(position)

    # Clamp power to motor speed limits
    power = max(min(power, MAX_SPEED), -MAX_SPEED)

    # Simulate system update over small time step
    dt = 0.1
    position += power * dt

    # Output state
    print(f"{now - start_time:.1f}\t{position:.3f}\t\t{power:.3f}\t\t{error:.3f}", end = '\r')

    time.sleep(dt)
