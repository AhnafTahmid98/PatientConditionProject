import time
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS

# Setup I2C bus and ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# Set up A0 channel for the heartbeat sensor by directly using 0 for A0
chan = AnalogIn(ads, 0)  # Reading from A0 channel

# Constants and variables for BPM calculation
pulse_threshold = 1.0  # Adjusted threshold voltage for detecting pulse peaks
pulse_intervals = []
last_pulse_time = None
bpm = 0

def calculate_bpm():
    """Calculates BPM based on the recorded pulse intervals."""
    global bpm, pulse_intervals
    if len(pulse_intervals) >= 5:  # Use last 5 intervals to calculate BPM
        avg_interval = sum(pulse_intervals) / len(pulse_intervals)
        bpm = 60000 / avg_interval  # BPM calculation from average interval
        pulse_intervals.clear()  # Clear intervals after calculating BPM
        print(f"Heart Rate: {bpm:.2f} BPM")
        print(f"Your BPM is {bpm:.2f}")

# Main loop for measuring heart rate
print("Starting heart rate measurement on A0...")

while True:
    voltage = chan.voltage
    print(f"Voltage on A0: {voltage:.3f} V")

    # Check for a pulse based on threshold crossing
    if voltage > pulse_threshold:
        current_time = time.time() * 1000  # Convert to milliseconds

        if last_pulse_time is None:
            print("Pulse detected (first pulse)")
            last_pulse_time = current_time
        else:
            interval = current_time - last_pulse_time
            last_pulse_time = current_time

            # Only record intervals that are within a reasonable range
            if 300 < interval < 2500:  # Adjusted range for possible pulse intervals
                print(f"Pulse detected. Interval since last pulse: {interval:.2f} ms")
                pulse_intervals.append(interval)
                if len(pulse_intervals) > 5:
                    pulse_intervals.pop(0)  # Keep only last 5 intervals
                calculate_bpm()
            else:
                print("Noise or abnormal pulse interval detected, skipping...")

    # Wait briefly before next reading
    time.sleep(0.1)
