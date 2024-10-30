import time
import board
import busio
from adafruit_ads1x15.ads import ADS  # Import ADS class instead of ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus and ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)  # Initialize ADS1115 object

# Select A1 as the input channel for heart rate measurement
chan = AnalogIn(ads, ADS.P1)  # Use ADS.P1 instead of ADS1115.P1

# Variables to measure BPM
previous_pulse_time = None
bpm_readings = []

print("Starting heart rate measurement...")

try:
    while True:
        # Read the voltage value from the sensor
        voltage = chan.voltage

        # Threshold voltage for detecting a pulse (you may need to adjust this value)
        threshold_voltage = 0.5

        # Detect pulse if voltage crosses the threshold
        if voltage > threshold_voltage:
            current_pulse_time = time.time() * 1000  # in milliseconds

            if previous_pulse_time:
                interval = current_pulse_time - previous_pulse_time
                bpm = 60000 / interval  # Calculate BPM from interval (ms to minutes)
                bpm_readings.append(bpm)

                # Keep the list of readings to last 5 only
                if len(bpm_readings) > 5:
                    bpm_readings.pop(0)

                # Calculate average BPM
                avg_bpm = sum(bpm_readings) / len(bpm_readings)
                
                print(f"Pulse detected. Interval since last pulse: {interval:.2f} ms")
                print(f"Heart Rate: {avg_bpm:.2f} BPM")
                print(f"Your BPM is {avg_bpm:.2f}")

            previous_pulse_time = current_pulse_time

        time.sleep(0.05)  # Slight delay for smoother readings

except KeyboardInterrupt:
    print("Measurement stopped by user.")
