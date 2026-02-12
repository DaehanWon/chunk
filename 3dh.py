import smbus
import time
import struct

# --- I2C Configuration ---
# Default Address for MLX90393 is usually 0x0C (or 0x19 depending on jumper)
DEVICE_ADDR = 0x0C 
BUS_NUM = 1

# --- MLX90393 Commands ---
CMD_SB = 0x10  # Start Burst Mode
CMD_SM = 0x30  # Start Single Measurement Mode
CMD_RM = 0x40  # Read Measurement
CMD_EX = 0x80  # Exit Mode

# --- Axis Bits (Which axes to measure) ---
# Bit 3: Temp, Bit 2: Z, Bit 1: Y, Bit 0: X
# 0xE = Z, Y, X (Binary 1110)
# 0xF = T, Z, Y, X (Binary 1111)
AXIS_MASK = 0x0E 

bus = smbus.SMBus(BUS_NUM)

def start_measurement():
    """ Sends command to start a single measurement for X, Y, Z """
    # Command byte: 0x30 (SM) | 0x0E (Axes)
    cmd = CMD_SM | AXIS_MASK
    try:
        bus.write_byte(DEVICE_ADDR, cmd)
    except OSError:
        print("Error: Sensor not responding. Check wiring or I2C Address.")
        exit()

def read_data():
    """ 
    Reads the measurement data.
    Order: Status, T(if enabled), X, Y, Z
    """
    # Command byte: 0x40 (RM) | 0x0E (Axes)
    cmd = CMD_RM | AXIS_MASK
    
    # We expect 1 status byte + 6 bytes of data (2 for X, 2 for Y, 2 for Z)
    # Total 7 bytes
    try:
        # Write the Read command and get the block of data
        data = bus.read_i2c_block_data(DEVICE_ADDR, cmd, 7)
    except OSError:
        return None

    # data[0] is Status Byte, ignore for now
    
    # Convert 2 bytes into 16-bit signed integer (Big Endian or Little Endian)
    # MLX90393 sends High byte then Low byte usually (Big Endian)
    # Note: If values look wrong, try swapping to Little Endian (data[x] | data[x+1]<<8)
    
    # Structure: Status, X_H, X_L, Y_H, Y_L, Z_H, Z_L
    x = (data[1] << 8) | data[2]
    y = (data[3] << 8) | data[4]
    z = (data[5] << 8) | data[6]

    # Convert to signed 16-bit integer
    if x > 32767: x -= 65536
    if y > 32767: y -= 65536
    if z > 32767: z -= 65536

    return x, y, z

print(f"Initializing 3D Hall Sensor (MLX90393) at address {hex(DEVICE_ADDR)}...")
print("Reading Magnetic Flux... (Press Ctrl+C to stop)")
print("-" * 50)

try:
    while True:
        # 1. Send 'Start Measurement' command
        start_measurement()
        
        # 2. Wait for conversion (approx 10-20ms)
        time.sleep(0.05)
        
        # 3. Read the result
        values = read_data()
        
        if values:
            x, y, z = values
            # Calculate magnitude (strength of magnet)
            magnitude = (x**2 + y**2 + z**2) ** 0.5
            
            print(f"X: {x:6} | Y: {y:6} | Z: {z:6} | Mag: {magnitude:.1f}")
        
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopped.")
