import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, ADS1115.P1)  # Using channel A1

print("Starting heart rate measurement...")
start_time = time.time()

try:
    while True:
        voltage = chan.voltage
        print(f"Voltage on A1: {voltage:.3f} V")
        time.sleep(1)
except KeyboardInterrupt:
    print("Measurement stopped by user.")
