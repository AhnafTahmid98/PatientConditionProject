import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# Initialize the I2C bus and devices
def initialize_devices():
    i2c_ads = busio.I2C(board.SCL, board.SDA)
    adc = ADS1115(i2c_ads)
    adc.gain = 1
    i2c_display = i2c(port=1, address=0x3C)  # Confirm address with i2cdetect if needed
    device = ssd1306(i2c_display)
    return adc, device

# Set up initial I2C devices
adc, device = initialize_devices()

# Moving average filter settings
window_size = 10  # Number of readings to average
readings = []

# Baseline and thresholds (adjust based on your observed baseline)
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

# Load Times New Roman or a similar font
font_path = "/usr/share/fonts/truetype/msttcorefonts/times.ttf"  # Adjust path if needed
font = ImageFont.truetype(font_path, 16)  # Adjust font size as needed

def read_gsr():
    # Read the analog value from channel 1 (A1)
    chan = AnalogIn(adc, 1)
    return chan.value

def get_moving_average(value):
    # Add the new reading to the list
    readings.append(value)
    
    # Keep only the last 'window_size' readings
    if len(readings) > window_size:
        readings.pop(0)
    
    # Calculate and return the average
    return sum(readings) / len(readings)

def determine_stress_level(smoothed_value):
    # Determine the stress level based on thresholds
    if smoothed_value < relaxed_threshold:
        return "Relaxed"
    elif relaxed_threshold <= smoothed_value < normal_threshold:
        return "Normal"
    elif normal_threshold <= smoothed_value < elevated_threshold:
        return "Elevated"
    else:
        return "High"

def display_stress_level(device, stress_level):
    # Display the stress level on the OLED screen with Times New Roman font
    with canvas(device) as draw:
        draw.text((10, 10), "Stress:", font=font, fill="white")
        draw.text((10, 30), stress_level, font=font, fill="white")

try:
    while True:
        try:
            gsr_value = read_gsr()
            smoothed_value = get_moving_average(gsr_value)
            
            # Determine contact status and stress level
            if smoothed_value < 13000:
                contact_status = "Contact with human detected"
                stress_level = determine_stress_level(smoothed_value)
                print(f"{contact_status} | Stress: {stress_level} | Smoothed GSR Value: {smoothed_value}")
                
                # Display the stress level on OLED
                display_stress_level(device, stress_level)
            else:
                print("No contact detected")
                display_stress_level(device, "No Contact")
            
            # Delay for a bit to observe changes over time
            time.sleep(2)  # Increase delay to reduce I2C load

        except OSError as e:
            print("I2C communication error detected. Reinitializing I2C bus...")
            adc, device = initialize_devices()  # Reinitialize the I2C devices

except KeyboardInterrupt:
    print("Program stopped.")
