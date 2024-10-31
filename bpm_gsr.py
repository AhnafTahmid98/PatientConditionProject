import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# Initialize the I2C bus and devices
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
ads.gain = 1
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Define OLED display fonts
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except IOError:
    font = ImageFont.load_default()

# Thresholds and settings for heart rate and GSR
heart_rate_channel = AnalogIn(ads, 2)  # Changed to A2 for heart rate
gsr_channel = AnalogIn(ads, 1)         # GSR remains on A1
high_threshold = 2.0  # Adjusted high threshold
low_threshold = 1.0   # Adjusted low threshold
min_pulse_interval = 0.3  # Minimum interval between pulses (in seconds)
last_pulse_time = 0
first_pulse = True
window_size = 10
hr_readings = []  # For smoothing heart rate data
gsr_readings = []
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

# Function to update OLED display
def update_oled(bpm, stress_level):
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), f"BPM: {int(bpm)}", font=font, fill=255)
    draw.text((0, 20), "Stress:", font=font, fill=255)
    draw.text((0, 40), stress_level, font=font, fill=255)
    oled.image(image)
    oled.show()

# Function to calculate moving average
def get_moving_average(value, readings):
    readings.append(value)
    if len(readings) > window_size:
        readings.pop(0)
    return sum(readings) / len(readings)

# Function to determine stress level from GSR readings
def determine_stress_level(smoothed_value):
    if smoothed_value < relaxed_threshold:
        return "Relaxed"
    elif relaxed_threshold <= smoothed_value < normal_threshold:
        return "Normal"
    elif normal_threshold <= smoothed_value < elevated_threshold:
        return "Elevated"
    else:
        return "High"

# Main loop to read heart rate and GSR, and update OLED
try:
    while True:
        # Read and smooth heart rate sensor data
        voltage = heart_rate_channel.voltage
        smoothed_voltage = get_moving_average(voltage, hr_readings)

        # Detect pulse and calculate BPM
        bpm = None
        if smoothed_voltage > high_threshold and first_pulse:
            last_pulse_time = time.time()
            first_pulse = False
        elif smoothed_voltage > high_threshold and (time.time() - last_pulse_time) > min_pulse_interval:
            pulse_interval = (time.time() - last_pulse_time) * 1000  # in ms
            last_pulse_time = time.time()
            bpm = 60000 / pulse_interval

        # Read and smooth GSR sensor data, then determine stress level
        gsr_value = gsr_channel.value
        smoothed_gsr_value = get_moving_average(gsr_value, gsr_readings)
        stress_level = determine_stress_level(smoothed_gsr_value)

        # Update OLED display
        update_oled(bpm if bpm else 0, stress_level)

        # Print data for debugging
        print(f"BPM: {bpm if bpm else 'Calculating...'}, Stress: {stress_level}, GSR Value: {smoothed_gsr_value}")

        # Delay for observation
        time.sleep(1)

except KeyboardInterrupt:
    print("Program stopped.")
