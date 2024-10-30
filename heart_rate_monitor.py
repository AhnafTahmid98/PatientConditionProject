import time
from adafruit_ads1x15 import ads1115
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio

# Set up I2C and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ads1115.ADS1115(i2c)

# Set up channels
chan_A0 = AnalogIn(ads, ads1115.P0)
chan_A1 = AnalogIn(ads, ads1115.P1)
chan_A2 = AnalogIn(ads, ads1115.P2)
chan_A3 = AnalogIn(ads, ads1115.P3)

print("Reading voltages on all channels...")

# Loop to read and display voltages
while True:
    voltage_A0 = chan_A0.voltage
    voltage_A1 = chan_A1.voltage
    voltage_A2 = chan_A2.voltage
    voltage_A3 = chan_A3.voltage
    
    print(f"Voltage on A0: {voltage_A0:.3f} V, A1: {voltage_A1:.3f} V, A2: {voltage_A2:.3f} V, A3: {voltage_A3:.3f} V")
    time.sleep(1)
