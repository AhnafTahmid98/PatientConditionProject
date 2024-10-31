import time
import board
import busio
import matplotlib.pyplot as plt
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ssd1306

# Setup I2C communication for OLED display and ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)  # Using channel A0 for heart rate sensor

# Initialize OLED display
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.show()

# Variables for pulse detection and data storage
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True
bpm_data = []
time_data = []

# Initialize plot
plt.ion()  # Enable interactive mode for live updating
fig, ax = plt.subplots()
start_time = time.time()

print("Starting heart rate measurement on A0...")

# Function to update OLED display with BPM
def update_oled(bpm):
    oled.fill(0)
    oled.text(f"BPM: {int(bpm)}", 0, 0, 1)
    oled.show()

# Main loop for pulse detection and live plot updating
try:
    while True:
        # Read current voltage from the sensor
        voltage = chan.voltage
        print(f"Voltage on A0: {voltage:.3f} V")

        # Detect pulse and calculate BPM
        if voltage > high_threshold and first_pulse:
            print("Pulse detected (first pulse)")
            last_pulse_time = time.time()
            first_pulse = False

        elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
            pulse_interval = (time.time() - last_pulse_time) * 1000  # in ms
            last_pulse_time = time.time()
            bpm = 60000 / pulse_interval
            print(f"Heart Rate: {bpm:.2f} BPM")

            # Update OLED and add data for plotting
            update_oled(bpm)
            bpm_data.append(bpm)
            time_data.append(time.time() - start_time)

            # Limit the graph data to last 50 points for clarity
            bpm_data_display = bpm_data[-50:]
            time_data_display = time_data[-50:]

            # Update the graph
            ax.clear()
            ax.plot(time_data_display, bpm_data_display, label="Heart Rate (BPM)")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Heart Rate (BPM)")
            ax.set_title("Real-Time Heart Rate")
            ax.legend(loc="upper right")
            plt.pause(0.1)  # Pause to allow for live plot updating

except KeyboardInterrupt:
    print("Heart rate monitoring stopped.")

finally:
    plt.ioff()  # Disable interactive mode
    plt.show()  # Show final plot if interrupted
