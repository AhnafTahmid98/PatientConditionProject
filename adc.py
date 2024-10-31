import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
ads.gain = 1  # Gain of 1 for a range of 4.096V

# Initialize channel A0 on ADS1115
channel = AnalogIn(ads, ADS1115.P0)

print("Reading from ADS1115 on A0...")
time.sleep(1)

try:
    while True:
        # Read the voltage from channel A0
        voltage = channel.voltage
        print(f"Voltage on A0: {voltage:.3f} V")

        # Wait a short time before the next reading
        time.sleep(1)

except KeyboardInterrupt:
    print("ADC test stopped.")
