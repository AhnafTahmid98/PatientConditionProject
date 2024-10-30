import time
import board
import busio
import matplotlib.pyplot as plt
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS1115

# Initialize I2C bus and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)

# Set up plot
plt.ion()  # Interactive mode on for live updating
fig, ax = plt.subplots()
time_data = []
voltage_data = []
bpm_data = []

# Peak detection variables
peak_threshold = 2.0  # Adjust this threshold based on your sensor output
min_time_between_peaks = 0.6  # Minimum interval between peaks in seconds (to avoid noise)
last_peak_time = 0
bpm = 0

# Start reading and plotting data
start_time = time.time()
while True:
    try:
        # Read data from the sensor
        voltage = chan.voltage
        current_time = time.time() - start_time
        voltage_data.append(voltage)
        time_data.append(current_time)
        
        # Check for peak detection
        if voltage > peak_threshold and (current_time - last_peak_time) > min_time_between_peaks:
            # Detected a peak
            if last_peak_time != 0:  # Ignore the first peak (no previous peak to calculate BPM)
                interval = current_time - last_peak_time
                bpm = 60 / interval
                bpm_data.append(bpm)
                
                # Print BPM
                print(f"BPM: {bpm:.2f}")
            
            last_peak_time = current_time

        # Plot the data
        ax.clear()
        ax.plot(time_data, voltage_data, label="Heart Rate (Voltage)")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title(f"Real-Time Heart Rate (BPM: {bpm:.2f})")
        ax.legend()

        # Display or save the plot
        plt.draw()
        plt.pause(0.1)

        # Limit data length for smoother plotting
        if len(time_data) > 100:
            time_data.pop(0)
            voltage_data.pop(0)
            if bpm_data:
                bpm_data.pop(0)

    except KeyboardInterrupt:
        print("Plotting stopped.")
        break
