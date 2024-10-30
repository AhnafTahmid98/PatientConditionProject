import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Set up I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS(i2c)
chan_A1 = AnalogIn(ads, ADS.P1)  # Using A1 as per your setup

# Constants
MIN_VALID_INTERVAL = 300  # Minimum interval in ms for a valid pulse
MAX_VALID_INTERVAL = 1500  # Maximum interval in ms for a valid pulse

# Variables
previous_pulse_time = None
bpm_values = []

def calculate_bpm(intervals):
    """Calculate BPM based on the average of pulse intervals."""
    if intervals:
        avg_interval = sum(intervals) / len(intervals)
        bpm = 60000 / avg_interval  # Convert ms to BPM
        return bpm
    return None

print("Starting heart rate measurement...")
pulse_intervals = []

try:
    while True:
        # Read the voltage on A1
        voltage = chan_A1.voltage

        # Detect pulse based on voltage threshold
        if voltage > 0.5:  # Adjust threshold as needed for stability
            current_time = time.time() * 1000  # Current time in ms

            if previous_pulse_time is not None:
                interval = current_time - previous_pulse_time

                # Only accept intervals within a valid range
                if MIN_VALID_INTERVAL <= interval <= MAX_VALID_INTERVAL:
                    pulse_intervals.append(interval)
                    print(f"Pulse detected. Interval since last pulse: {interval:.2f} ms")

                    # Calculate BPM if we have enough intervals
                    if len(pulse_intervals) >= 5:  # Average over last 5 intervals
                        bpm = calculate_bpm(pulse_intervals[-5:])
                        print(f"Heart Rate: {bpm:.2f} BPM")
                        if 60 <= bpm <= 100:
                            print(f"Your BPM is {bpm:.2f} - Normal")
                        else:
                            print(f"Your BPM is {bpm:.2f} - Out of normal range")

                else:
                    print("Noise or abnormal pulse interval detected, skipping...")

            previous_pulse_time = current_time

        time.sleep(0.05)  # Small delay to avoid rapid polling

except KeyboardInterrupt:
    print("Measurement stopped by user.")
except ImportError as e:
    print(f"Import error: {e}. Please check library installation.")
finally:
    print("Exiting program gracefully.")
