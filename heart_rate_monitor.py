import time
from adafruit_ads1x15.ads1115 import ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
import statistics

# Setup for I2C communication and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS(i2c)
chan = AnalogIn(ads, ADS.P0)  # Using channel A0

# Parameters for adaptive thresholding and pulse calculation
window_size = 10  # Number of samples for adaptive threshold
voltage_samples = []
threshold_high = 2.5
threshold_low = 1.6
pulse_last_time = None
min_pulse_interval = 300  # Minimum interval in ms for a valid pulse
bpm_values = []

print("Starting heart rate measurement on A0...")

while True:
    voltage = chan.voltage
    print(f"Voltage on A0: {voltage:.3f} V")

    # Update voltage samples and adapt thresholds
    voltage_samples.append(voltage)
    if len(voltage_samples) > window_size:
        voltage_samples.pop(0)  # Maintain a fixed sample window
        threshold_high = max(voltage_samples) * 0.75
        threshold_low = min(voltage_samples) * 0.5
        print(f"Updated thresholds - High: {threshold_high:.3f}, Low: {threshold_low:.3f}")

    # Detect pulse when voltage crosses the high threshold
    if voltage > threshold_high:
        current_time = time.time()
        if pulse_last_time:
            interval = (current_time - pulse_last_time) * 1000  # Convert to milliseconds
            if interval >= min_pulse_interval:
                bpm = 60000 / interval  # Calculate BPM
                bpm_values.append(bpm)
                print(f"Pulse detected. Interval: {interval:.2f} ms")
                print(f"Heart Rate: {bpm:.2f} BPM")
                print(f"Your BPM is {bpm:.2f}")
            else:
                print("Noise or abnormal pulse interval detected, skipping...")
        pulse_last_time = current_time

    time.sleep(0.1)  # Adjust delay as necessary
