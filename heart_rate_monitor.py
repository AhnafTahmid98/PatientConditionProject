import time
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio

# Setup I2C communication and initialize the ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)  # Use 0 directly for channel A0

# Variables for pulse detection
high_threshold = 2.5  # Example voltage threshold for pulse detection
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

print("Starting heart rate measurement on A0...")

try:
    while True:
        voltage = chan.voltage
        print(f"Voltage on A0: {voltage:.3f} V")

        if voltage > high_threshold and first_pulse:
            print("Pulse detected (first pulse)")
            last_pulse_time = time.time()
            first_pulse = False

        elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
            pulse_interval = (time.time() - last_pulse_time) * 1000  # in ms
            last_pulse_time = time.time()
            bpm = 60000 / pulse_interval
            print(f"Pulse detected. Interval: {pulse_interval:.2f} ms")
            print(f"Heart Rate: {bpm:.2f} BPM")
            print(f"Your BPM is {bpm:.2f}")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")
