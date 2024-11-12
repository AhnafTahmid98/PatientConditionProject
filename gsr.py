import time
import board
import busio
import threading
import signal
import sys
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

# LED and buzzer pin definitions
green_led = 17  # GPIO 17
yellow_led = 27  # GPIO 27
red_led = 22    # GPIO 22
buzzer_pin = 23 # GPIO 23

# GPIO setup for LEDs and buzzer
GPIO.setmode(GPIO.BCM)
GPIO.setup(green_led, GPIO.OUT)
GPIO.setup(yellow_led, GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)
GPIO.setup(buzzer_pin, GPIO.OUT)

# Initialize I2C bus, ADC, and OLED display
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c, address=0x48)
adc.gain = 1
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)

# Shared variables
stress_level = "None"
human_interaction = False

# Data lock
data_lock = threading.Lock()
running = True  # Flag to control threads

# Thresholds for GSR
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

# Function to set LED and buzzer based on stress level and human interaction
def set_leds_and_buzzer(status, interaction):
    GPIO.output(green_led, GPIO.HIGH if status in ["Normal", "Relaxed"] and interaction else GPIO.LOW)
    GPIO.output(yellow_led, GPIO.HIGH if status == "Elevated" and interaction else GPIO.LOW)
    GPIO.output(red_led, GPIO.HIGH if status == "High" and interaction else GPIO.LOW)
    GPIO.output(buzzer_pin, GPIO.HIGH if status == "High" and interaction else GPIO.LOW)

# Function to determine stress level based on GSR reading
def determine_stress_level(gsr_value):
    global human_interaction
    if gsr_value < 13000:  # Threshold for human interaction
        human_interaction = True
        if gsr_value < relaxed_threshold:
            return "Relaxed"
        elif gsr_value < normal_threshold:
            return "Normal"
        elif gsr_value < elevated_threshold:
            return "Elevated"
        else:
            return "High"
    else:
        human_interaction = False
        return "NO-CONTACT"

# GSR Monitoring
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

def monitor_gsr():
    global stress_level
    while running:
        try:
            gsr_value = read_gsr()
            stress_level = determine_stress_level(gsr_value)
            with data_lock:
                print(f"GSR Value: {gsr_value}, Stress Level: {stress_level}, Interaction: {human_interaction}")
            # Save stress level to a file for command_server.py
            with open("/home/pi/PatientConditionProject/gsr_data.txt", "w") as f:
                f.write(stress_level)
            set_leds_and_buzzer(stress_level, human_interaction)
            time.sleep(3)
        except OSError:
            print("GSR error, reinitializing...")
            time.sleep(1)

# OLED Display Thread
def update_display():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
    except IOError:
        font = ImageFont.load_default()
    
    while running:
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

# Graceful exit function
def cleanup_and_exit(signum, frame):
    global running
    running = False
    set_leds_and_buzzer("Normal", False)  # Turn off all LEDs and buzzer on exit
    GPIO.cleanup()
    sys.exit(0)

# Main function
if __name__ == "__main__":
    # Register signal handlers for graceful exit in the main function
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    try:
        # Start threads for monitoring GSR and updating the display
        gsr_thread = threading.Thread(target=monitor_gsr)
        display_thread = threading.Thread(target=update_display)
        
        gsr_thread.start()
        display_thread.start()

        gsr_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        cleanup_and_exit(None, None)