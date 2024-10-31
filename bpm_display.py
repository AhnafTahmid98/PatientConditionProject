import time
import board
import busio
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
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

print("Starting heart rate measurement on A0...")

# Function to update OLED display with BPM
def update_oled(bpm):
    oled.fill(0)
    oled.text(f"BPM: {int(bpm)}", 0, 0, 1)
    oled.show()

# Function to update real-time plot
def animate(i):
    # Read current voltage from the sensor
    voltage = chan.voltage
    print(f"Voltage on A0: {voltage:.3f} V")

    # Detect pulse and calculate BPM
    global last_pulse_time, first_pulse
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
    plt.cla()
    plt.plot(time_data_display, bpm_data_display, label="Heart Rate (BPM)")
    plt.xlabel("Time (s)")
    plt.ylabel("Heart Rate (BPM)")
    plt.title("Real-Time Heart Rate")
    plt.legend(loc="upper right")

# Initialize plot
plt.style.use("ggplot")
fig = plt.figure()

# Start real-time animation and keep reference to prevent garbage collection
start_time = time.time()
global ani  # Make `ani` a global variable to keep it in memory
ani = FuncAnimation(fig, animate, interval=1000, cache_frame_data=False)

# Display the plot
plt.show()
