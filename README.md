# Robot Tour

Software for my Science Olympiad **Robot Tour** robots (2025 and 2026 seasons): a desktop
route planner that solves the course, the on-robot drive code that runs it, and custom gyro
firmware that keeps the robot pointed the right way.

In Robot Tour, an autonomous robot drives a grid of 50 cm squares. It has to pass through
gate zones, avoid walls, and stop on a target point as close as possible to a target time
that is only announced at the competition. The course layout is revealed on the day, so the
route has to be planned and loaded quickly.

## What's in here

| Folder | What it is | Stack |
| --- | --- | --- |
| [`gridding/`](gridding) | Course editor and optimal route planner | Python, pygame |
| [`RobotTour2026/`](RobotTour2026) | Current robot: drive code and gyro firmware | Pybricks MicroPython (EV3), Arduino C++ |
| [`RobotTour2025/`](RobotTour2025) | Previous season's robot code | Pybricks MicroPython (EV3) |
| [`testing/`](testing) | PID controller simulation | Python |

## Route planner (`gridding/`)

A pygame app where I click the day's course onto a grid (start, target, gates, walls, bottles)
and it computes the cheapest legal route.

- **Solver:** dynamic programming over bitmasks of visited gates and scored bottles, memoized
  with `lru_cache`, with a shortest-path search between waypoints. The state also tracks the
  robot's heading, because turns cost time and the planner should prefer straighter routes.
- **Rule-aware:** handles walls on grid edges, bottles that must be carried into gates, and
  the "last gate" bonus. Each mechanic is a toggle at the top of the file, since the rules
  change between seasons.
- **Output:** a command queue such as `ENTER, LEFT, FORWARD2, RIGHT, BUMP, ..., EXIT` that
  pastes straight into the robot program, plus a difficulty estimate for the route.
- The solve runs on a worker thread so the interface stays responsive.
- `griddingAnalog.py` is a console-only version of the same planner, kept as a fallback.

## Robot code (`RobotTour2026/`)

`main.py` runs on a LEGO EV3 brick under Pybricks MicroPython.

- **Hits the target time automatically.** `initQueue` counts the moves in the route, subtracts
  the fixed time spent on turns and pauses, and solves for the one drive speed that makes the
  whole run finish on the target time.
- **Heading-hold driving.** Straight segments run a proportional controller on gyro error and
  snap to the nearest 90° heading, with square-root acceleration ramps at both ends.
- **Two-stage turns.** A fast coarse turn, then a slow correction onto the exact grid heading.
- **Odometry.** Tracks world-frame position from wheel distance and heading.

### Custom gyro (`gyro_code*/`)

The stock EV3 gyro drifted too much to hold a heading over a full run, so I replaced it with an
ICM-20948 IMU on an Arduino that talks to the EV3 over UART (`h` returns the heading, `r`
resets, `c` calibrates). The firmware went through three versions; `gyro_code_v3` is current:

- Fits a **linear drift model** during calibration with online least-squares regression, and
  stores the result in EEPROM so the robot does not need recalibrating on every boot.
- **Zero-velocity updates:** a rolling variance window detects when the robot is stationary and
  slowly corrects the bias estimate, with a lockout period after each turn.

## Running it

**Planner**

```bash
pip install pygame
cd gridding
python gridding.py
```

Set `ROOT` near the bottom of `gridding.py` to your local `gridding/assets` folder first.

**Robot**

Flash an EV3 with [ev3dev](https://pybricks.com/ev3-micropython/startinstall.html), open
`RobotTour2026/` in VS Code with the LEGO EV3 MicroPython extension, paste the planner's queue
and target time into the top of `main.py`, and download it to the brick. Upload
`gyro_code_v3/gyro_code_v3.ino` to the Arduino with the SparkFun ICM-20948 library installed.

Wheel size, track width, and the tuning constants in `params` and `times` are specific to my
robot and will need re-measuring for any other build.

## Credits

Built by Siddharth Nair. Interface font: [Cascadia Code](https://github.com/microsoft/cascadia-code)
(SIL Open Font License).
