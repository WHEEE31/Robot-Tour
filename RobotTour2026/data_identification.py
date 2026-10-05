
from pybricks.iodevices import UARTDevice
from pybricks.parameters import Port
from pybricks.tools import wait

# Change Port.S4 to whichever port you are using
port = Port.S4

try:
    print("Opening Port...")
    ser = UARTDevice(port, 115200)
    print("Port Open. Listening for Arduino...")
except Exception as e:
    print("Could not open port:", e)
    exit()

while True:
    # Check if any bytes are waiting in the buffer
    if ser.waiting() > 0:
        # Read everything available
        data = ser.read_all()
        
        # Try to decode it as text, but show raw bytes if it fails
        try:
            print("Received:", data.decode().strip())
        except:
            print("Raw Data (Possible Noise):", data)
    
    wait(10) # Small 10ms nap to keep the CPU happy