import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
ads.gain = 1  # Gain of 1 for a range of 4.096V

# Initialize channels using numeric indexing 0, 1, 2, and 3
channels = [
    AnalogIn(ads, 0),  # A0
    AnalogIn(ads, 1),  # A1
    AnalogIn(ads, 2),  # A2
    AnalogIn(ads, 3)   # A3
]

print("Reading from ADS1115 on channels A0, A1, A2, and A3...")
time.sleep(1)

try:
    while True:
        # Read the voltage from each channel and print the results
        for i, channel in enumerate(channels):
            voltage = channel.voltage
            print(f"Voltage on A{i}: {voltage:.3f} V")
        
        # Wait a short time before the next reading
        time.sleep(1)
        print("-" * 30)

except KeyboardInterrupt:
    print("ADC test stopped.")
