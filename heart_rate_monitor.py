import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Set up I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS(i2c)
chan_A1 = AnalogIn(ads, ADS.P1)

# Constants
MIN_VALID_INTERVAL = 300  # Minimum interval in ms to be considered a valid heartbeat
MAX_VALID_INTERVAL = 1500  # Maximum interval in ms to be considered a valid heartbeat

# Variables
previous_pulse_time = None
bpm_values = []

def calculate_bpm(intervals):
    if len(intervals) > 0:
        avg_interval = sum(intervals) / len(intervals)
        bpm = 60000 / avg_interval
        return bpm
    return None

print("Starting heart rate measurement...")
pulse_intervals = []

while True:
    try:
        # Read the voltage on A1
        voltage = chan_A1.voltage

        # Detect pulse based on voltage threshold (adjust as needed)
        if voltage > 0.5:  # Threshold for pulse detection; adjust based on your sensor
            current_time = time.time() * 1000  # Current time in ms

            if previous_pulse_time is not None:
                interval = current_time - previous_pulse_time

                # Only consider intervals within a valid range
                if MIN_VALID_INTERVAL <= interval <= MAX_VALID_INTERVAL:
                    pulse_intervals.append(interval)
                    print(f"Pulse detected. Interval since last pulse: {interval:.2f} ms")

                    # Calculate BPM if there are enough intervals
                    if len(pulse_intervals) >= 5:  # Average over 5 intervals for stability
                        bpm = calculate_bpm(pulse_intervals[-5:])
                        print(f"Heart Rate: {bpm:.2f} BPM")
                        if 60 <= bpm <= 100:
                            print(f"Your BPM is {bpm:.2f} - Normal")
                        else:
                            print(f"Your BPM is {bpm:.2f} - Out of normal range")

                else:
                    print("Noise or abnormal pulse interval detected, skipping...")

            previous_pulse_time = current_time

        time.sleep(0.05)  # Delay to avoid rapid polling

    except KeyboardInterrupt:
        print("Measurement stopped by user.")
        break
