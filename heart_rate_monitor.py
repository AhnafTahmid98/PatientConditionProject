import time
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS(i2c)

# Set up channels A0 and A1 for testing
chan_A0 = AnalogIn(ads, ADS.P0)
chan_A1 = AnalogIn(ads, ADS.P1)

try:
    print("Reading raw values from ADS1115 on A0 and A1...")
    while True:
        # Read voltage from A0 and A1
        voltage_A0 = chan_A0.voltage
        voltage_A1 = chan_A1.voltage
        print(f"Voltage on A0: {voltage_A0:.3f} V, Voltage on A1: {voltage_A1:.3f} V")
        
        time.sleep(0.5)  # Read every 0.5 seconds

except KeyboardInterrupt:
    print("Stopped by user.")
