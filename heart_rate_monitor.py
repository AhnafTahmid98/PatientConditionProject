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
plt.ion()  # Interactive mode on for live updating (only works with display environment)
fig, ax = plt.subplots()
time_data = []
heart_rate_data = []

# Start reading and plotting data
start_time = time.time()
frame_count = 0  # Counter to save periodic frames

while True:
    try:
        # Read data from the sensor
        voltage = chan.voltage
        heart_rate_data.append(voltage)
        time_data.append(time.time() - start_time)
        
        # Debug print to verify readings
        print(f"Time: {time_data[-1]:.2f}s, Voltage: {voltage:.2f}V")

        # Plot the data
        ax.clear()
        ax.plot(time_data, heart_rate_data, label="Heart Rate (Voltage)")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Real-Time Heart Rate")
        ax.legend()
        
        # Display the plot or save it as an image
        plt.draw()
        plt.pause(0.1)  # Update interval

        # Save the plot periodically if headless (every 10 frames, for example)
        frame_count += 1
        if frame_count % 10 == 0:
            plt.savefig("heart_rate_plot.png")  # Saves the current plot frame

        # Limit data length for smoother plotting
        if len(time_data) > 100:
            time_data.pop(0)
            heart_rate_data.pop(0)

    except KeyboardInterrupt:
        print("Plotting stopped.")
        break
