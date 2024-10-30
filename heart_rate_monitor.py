import time
try:
    from adafruit_ads1x15.ads1115 import ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import board
    import busio
    print("ADS and AnalogIn modules imported successfully!")
except ImportError as e:
    print(f"Import error: {e}")
    exit()

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS(i2c)

# Create an analog input channel on A1
try:
    chan = AnalogIn(ads, ADS.P1)
    print("Analog channel on A1 initialized successfully!")
except AttributeError as e:
    print(f"Attribute error: {e}")
    exit()

# Reading loop for testing
print("Starting voltage readings on A1...")
try:
    while True:
        print(f"Voltage on A1: {chan.voltage:.3f} V")
        time.sleep(1)
except KeyboardInterrupt:
    print("Measurement stopped by user.")
