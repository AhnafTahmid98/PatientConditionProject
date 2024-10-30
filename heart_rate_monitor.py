import time
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS1115

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)

try:
    print("Reading raw values from ADS1115...")
    while True:
        voltage = chan.voltage
        print(f"Voltage: {voltage:.3f} V")
        time.sleep(0.5)  # Read every 0.5 seconds
except KeyboardInterrupt:
    print("Stopped by user.")
