import time
import board
import busio
from adafruit_ads1x15.ads import ADS  # Import the ADS class correctly
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS1115  # Import the ADS1115 class

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, ADS.P1)  # Use ADS.P1 to reference channel A1

print("Starting heart rate measurement...")
start_time = time.time()

try:
    while True:
        voltage = chan.voltage
        print(f"Voltage on A1: {voltage:.3f} V")
        time.sleep(1)
except KeyboardInterrupt:
    print("Measurement stopped by user.")
