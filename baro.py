import smbus
import time

# --- BMP280 Registers ---
# Default I2C address (Change to 0x77 if 0x76 doesn't work)
DEVICE_ADDR = 0x76 

# Register Addresses
REG_DATA    = 0xF7
REG_CONTROL = 0xF4
REG_CONFIG  = 0xF5
REG_CALIB   = 0x88

# --- I2C Setup ---
bus = smbus.SMBus(1)

def get_short(data, index):
    """ Helper to read signed 16-bit integer from data list """
    return (data[index+1] << 8) + data[index]

def get_ushort(data, index):
    """ Helper to read unsigned 16-bit integer from data list """
    return (data[index+1] << 8) + data[index]

def read_calibration_data():
    """ 
    Reads factory calibration coefficients.
    Required to convert raw data into readable temperature/pressure.
    """
    calib = bus.read_i2c_block_data(DEVICE_ADDR, REG_CALIB, 24)
    dig = {}
    
    dig['T1'] = get_ushort(calib, 0)
    dig['T2'] = (calib[3] << 8) | calib[2] # Signed
    if dig['T2'] > 32767: dig['T2'] -= 65536
    dig['T3'] = (calib[5] << 8) | calib[4] # Signed
    if dig['T3'] > 32767: dig['T3'] -= 65536

    dig['P1'] = get_ushort(calib, 6)
    dig['P2'] = (calib[9] << 8) | calib[8]
    if dig['P2'] > 32767: dig['P2'] -= 65536
    dig['P3'] = (calib[11] << 8) | calib[10]
    if dig['P3'] > 32767: dig['P3'] -= 65536
    dig['P4'] = (calib[13] << 8) | calib[12]
    if dig['P4'] > 32767: dig['P4'] -= 65536
    dig['P5'] = (calib[15] << 8) | calib[14]
    if dig['P5'] > 32767: dig['P5'] -= 65536
    dig['P6'] = (calib[17] << 8) | calib[16]
    if dig['P6'] > 32767: dig['P6'] -= 65536
    dig['P7'] = (calib[19] << 8) | calib[18]
    if dig['P7'] > 32767: dig['P7'] -= 65536
    dig['P8'] = (calib[21] << 8) | calib[20]
    if dig['P8'] > 32767: dig['P8'] -= 65536
    dig['P9'] = (calib[23] << 8) | calib[22]
    if dig['P9'] > 32767: dig['P9'] -= 65536
    
    return dig

def setup_sensor():
    """ Initializes the sensor to 'Normal Mode' """
    # Write to Control Measurement Register (0xF4)
    # Mode: Normal (11) | Oversampling: x16 (standard)
    bus.write_byte_data(DEVICE_ADDR, REG_CONTROL, 0x27)
    
    # Write to Config Register (0xF5)
    # Filter: x16 | Standby: 500ms
    bus.write_byte_data(DEVICE_ADDR, REG_CONFIG, 0xA0)

def read_data(dig):
    """ Reads raw data and calculates Temperature & Pressure """
    
    # Read 6 bytes of data (Pressure MSB, LSB, XLSB, Temp MSB, LSB, XLSB)
    data = bus.read_i2c_block_data(DEVICE_ADDR, REG_DATA, 6)
    
    # Convert raw data (20-bit)
    adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)

    # --- Temperature Calculation (Bosch Formula) ---
    var1 = (adc_t / 16384.0 - dig['T1'] / 1024.0) * dig['T2']
    var2 = ((adc_t / 131072.0 - dig['T1'] / 8192.0) ** 2) * dig['T3']
    t_fine = var1 + var2
    temp_c = t_fine / 5120.0

    # --- Pressure Calculation (Bosch Formula) ---
    var1 = (t_fine / 2.0) - 64000.0
    var2 = var1 * var1 * dig['P6'] / 32768.0
    var2 = var2 + var1 * dig['P5'] * 2.0
    var2 = (var2 / 4.0) + (dig['P4'] * 65536.0)
    var1 = (dig['P3'] * var1 * var1 / 524288.0 + dig['P2'] * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * dig['P1']

    if var1 == 0:
        pressure = 0
    else:
        p = 1048576.0 - adc_p
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = dig['P9'] * p * p / 2147483648.0
        var2 = p * dig['P8'] / 32768.0
        pressure = p + (var1 + var2 + dig['P7']) / 16.0
    
    # Convert Pascals to hPa
    return temp_c, pressure / 100.0

# --- Main Program ---
try:
    print(f"Connecting to BMP280 at address {hex(DEVICE_ADDR)}...")
    setup_sensor()
    calib_coeffs = read_calibration_data()
    print("Calibration data loaded.")
    print("Reading Data... (Press Ctrl+C to stop)")
    print("-" * 40)

    while True:
        temp, press = read_data(calib_coeffs)
        
        # Calculate Altitude (approximate, based on sea level 1013.25 hPa)
        altitude = 44330 * (1.0 - (press / 1013.25) ** 0.1903)

        print(f"Temp: {temp:.2f} °C  |  Pressure: {press:.2f} hPa  |  Alt: {altitude:.2f} m")
        time.sleep(1)

except OSError as e:
    print(f"\n[Error] Sensor not found at address {hex(DEVICE_ADDR)}.")
    print("1. Check wiring (SDA/SCL)")
    print("2. Try changing DEVICE_ADDR to 0x77 in the code.")
    print("3. Run 'i2cdetect -y 1' to confirm address.")

except KeyboardInterrupt:
    print("\nMeasurement stopped.")
