import time
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS1115

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)

# Set up the channel to read from A1
chan = AnalogIn(ads, 1)  # Use A1

# Parameters for heartbeat detection
threshold_voltage = 0.55  # Adjusted threshold for detecting a pulse
pulse_intervals = []
last_pulse_time = None

print("Starting heart rate measurement...")

try:
    while True:
        # Read the voltage from A1
        voltage = chan.voltage
        current_time = time.time() * 1000  # Current time in milliseconds

        # Detect pulse based on threshold
        if voltage > threshold_voltage:
            if last_pulse_time is None:
                # First pulse detected
                last_pulse_time = current_time
                print("Pulse detected (first pulse)")
            else:
                # Calculate interval since last pulse
                interval = current_time - last_pulse_time
                if 300 < interval < 1500:  # Adjusted interval limits (300ms to 1500ms) for filtering
                    pulse_intervals.append(interval)
                    print(f"Pulse detected. Interval since last pulse: {interval:.2f} ms")
                    last_pulse_time = current_time
                else:
                    # Detected noise or an abnormal interval
                    print("Noise or abnormal pulse interval detected, skipping...")
                    last_pulse_time = current_time

            # Calculate BPM if we have at least 5 intervals
            if len(pulse_intervals) >= 5:
                avg_interval = sum(pulse_intervals) / len(pulse_intervals)
                bpm = 60000 / avg_interval  # Convert average interval to BPM
                print(f"Heart Rate: {bpm:.2f} BPM")
                print(f"Your BPM is {bpm:.2f}")
                
                # Clear intervals for fresh calculation
                pulse_intervals.clear()

        # Wait a short time before reading again
        time.sleep(0.05)  # Adjust sample rate if necessary

except KeyboardInterrupt:
    print("Measurement stopped by user.")
