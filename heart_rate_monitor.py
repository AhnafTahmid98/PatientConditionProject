import time
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1115 as ADS
import board
import busio

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, 0)  # Use channel A0 directly

# Variables for dynamic thresholding
peak_window = []
threshold_high = 2.5  # Initial high threshold
threshold_low = 1.0  # Initial low threshold
window_size = 10     # Number of recent peaks to track

# Variables for detecting heart rate
last_pulse_time = None
bpm = None

def update_thresholds():
    """Update dynamic thresholds based on recent peak values."""
    global threshold_high, threshold_low
    if peak_window:
        max_peak = max(peak_window)
        threshold_high = max_peak * 0.75
        threshold_low = max_peak * 0.5
    print(f"Updated thresholds - High: {threshold_high}, Low: {threshold_low}")

print("Starting heart rate measurement on A0...")

while True:
    voltage = chan.voltage
    print(f"Voltage on A0: {voltage:.3f} V")

    # Check if voltage exceeds high threshold (pulse detected)
    if voltage > threshold_high:
        # Update peak window and thresholds dynamically
        if not peak_window or voltage > max(peak_window):
            peak_window.append(voltage)
            if len(peak_window) > window_size:
                peak_window.pop(0)
            update_thresholds()

        # Calculate BPM based on time interval
        if last_pulse_time:
            interval = time.time() - last_pulse_time
            if interval > 0.3:  # Minimum interval to avoid noise
                bpm = 60 / interval
                print(f"Pulse detected. Interval: {interval*1000:.2f} ms")
                print(f"Heart Rate: {bpm:.2f} BPM")
                print(f"Your BPM is {bpm:.2f}")
            last_pulse_time = time.time()
        else:
            # First pulse detected
            print("Pulse detected (first pulse)")
            last_pulse_time = time.time()

    time.sleep(0.1)  # Adjust delay as necessary
