import time
from adafruit_ads1x15 import ads1115
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio

# Set up I2C and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ads1115.ADS1115(i2c)
chan = AnalogIn(ads, ads1115.P1)  # Using A1

print("Starting heart rate measurement...")

# Heart rate measurement logic here
while True:
    voltage = chan.voltage
    print(f"Voltage on A1: {voltage:.3f} V")
    time.sleep(0.5)
