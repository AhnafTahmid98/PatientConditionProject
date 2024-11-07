import time
import board
import busio
import threading
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

# LED and buzzer pin definitions
GREEN_LED = 17  # GPIO 17
YELLOW_LED = 27  # GPIO 27
RED_LED = 22  # GPIO 22
BUZZER_PIN = 23  # GPIO 23

# GPIO setup for LEDs and buzzer
GPIO.setmode(GPIO.BCM)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(YELLOW_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Initialize I2C bus and ADC
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c, address=0x48)
adc.gain = 1

# Initialize OLED display
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)

# Shared variables
stress_level = "None"
human_interaction = False

# Thresholds for GSR (assuming a baseline GSR reading)
BASELINE_VALUE = 11000
RELAXED_THRESHOLD = BASELINE_VALUE * 0.9
NORMAL_THRESHOLD = BASELINE_VALUE * 1.1
ELEVATED_THRESHOLD = BASELINE_VALUE * 1.3

# Function to control LEDs and buzzer based on stress level and interaction status
def set_leds_and_buzzer(stress, interaction):
    GPIO.output(GREEN_LED, GPIO.HIGH if stress == "Normal" else GPIO.LOW)
    GPIO.output(YELLOW_LED, GPIO.HIGH if stress == "Elevated" else GPIO.LOW)
    GPIO.output(RED_LED, GPIO.HIGH if stress == "High" and interaction else GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.HIGH if stress == "High" and interaction else GPIO.LOW)

# Function to assess stress level based on GSR value
def determine_stress_level(gsr_value):
    global human_interaction
    if gsr_value < 13000:  # Indicate human interaction
        human_interaction = True
        if gsr_value < RELAXED_THRESHOLD:
            return "Normal"
        elif gsr_value < NORMAL_THRESHOLD:
            return "Normal"
        elif gsr_value < ELEVATED_THRESHOLD:
            return "Elevated"
        else:
            return "High"
    else:
        human_interaction = False
        return "No contact"

# Function to read GSR value from the sensor
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

# GSR monitoring function to update stress level and control LEDs and buzzer
def monitor_gsr():
    global stress_level
    while True:
        try:
            gsr_value = read_gsr()
            stress_level = determine_stress_level(gsr_value)
            set_leds_and_buzzer(stress_level, human_interaction)
            print(f"GSR Value: {gsr_value}, Stress Level: {stress_level}, Interaction: {human_interaction}")
            time.sleep(3)
        except OSError:
            print("GSR error, reinitializing...")
            time.sleep(1)

# OLED display function to show stress level and interaction status
def update_display():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
    except IOError:
        font = ImageFont.load_default()
    
    while True:
        # Create a blank image for drawing
        image = Image.new("1", (128, 32))
        draw = ImageDraw.Draw(image)
        
        # Display Stress Level and Interaction Status
        draw.text((0, 0), f"Stress: {stress_level}", font=font, fill=255)
        draw.text((0, 16), f"Interaction: {'Yes' if human_interaction else 'No'}", font=font, fill=255)

        # Update OLED display
        oled.image(image)
        oled.show()
        
        time.sleep(1.5)

# Main function to run monitoring and display threads
if __name__ == "__main__":
    try:
        # Start threads for monitoring GSR and updating the display
        gsr_thread = threading.Thread(target=monitor_gsr)
        display_thread = threading.Thread(target=update_display)
        
        gsr_thread.start()
        display_thread.start()

        gsr_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        print("Monitoring stopped.")
        GPIO.cleanup()
