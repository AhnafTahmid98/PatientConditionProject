import time
import board
import busio
import threading
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import signal
import sys

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

# Initialize I2C bus, ADC and Oled Display
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c, address=0x48)
adc.gain = 1
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)

# Shared variables
bpm_value = 0
status = "Normal"
bpm_history = []  # For storing recent BPM values for graphing
human_interaction = False  # Tracks if human interaction is detected

# Heart rate thresholds and variables
high_threshold = 2.5  # Voltage thresholds for pulse detection
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

# GSR threshold for detecting human interaction
gsr_human_threshold = 13000  # Adjust based on your observations

# Lock for synchronizing data access
data_lock = threading.Lock()
running = True

# BPM thresholds for status levels
normal_bpm_range = (60, 100)
warning_bpm_range = (50, 120)

# Function to set LED and buzzer based on status
def set_leds_and_buzzer(status):
    GPIO.output(green_led, GPIO.HIGH if status == "Normal" else GPIO.LOW)
    GPIO.output(yellow_led, GPIO.HIGH if status == "Warning" else GPIO.LOW)
    GPIO.output(red_led, GPIO.HIGH if status == "Critical" else GPIO.LOW)
    GPIO.output(buzzer_pin, GPIO.HIGH if status == "Critical" else GPIO.LOW)

# Update status based on BPM value
def update_status():
    global status
    if bpm_value < 50 or bpm_value > 120:
        status = "Critical"
    elif 50 <= bpm_value < 60 or 100 < bpm_value <= 120:
        status = "Warning"
    else:
        status = "Normal"
    set_leds_and_buzzer(status)

# Function to check human interaction using GSR sensor
def check_human_interaction():
    chan_gsr = AnalogIn(adc, 1)
    gsr_value = chan_gsr.value
    return gsr_value < gsr_human_threshold  # Returns True if human interaction detected

# Heart Rate Monitoring
def monitor_heart_rate():
    global bpm_value, bpm_history, last_pulse_time, first_pulse, running, human_interaction
    while running:
        try:
            # Check for human interaction with GSR sensor
            human_interaction = check_human_interaction()
            
            if human_interaction:  # Only measure BPM if human interaction is detected
                chan_heart_rate = AnalogIn(adc, 0)
                voltage = chan_heart_rate.voltage
                current_time = time.time()
                
                # Detecting the pulse
                if voltage > high_threshold and first_pulse:
                    last_pulse_time = current_time
                    first_pulse = False
                elif voltage > high_threshold and (current_time - last_pulse_time) > 0.4:
                    pulse_interval = (current_time - last_pulse_time) * 1000  # Convert to milliseconds
                    bpm_value = 60000 / pulse_interval
                    last_pulse_time = current_time

                    # Update BPM history for graphing
                    with data_lock:
                        bpm_history.append(bpm_value)
                        if len(bpm_history) > 20:  # Limit history length
                            bpm_history.pop(0)
                        print(f"Heart Rate: {bpm_value:.2f} BPM")
                    
                    # Write the current BPM value to a file
                    with open("/home/pi/PatientConditionProject/bpm_data.txt", "w") as f:
                        f.write(str(bpm_value))
                    
                    # Update status based on new BPM value
                    update_status()
            else:
                # Reset BPM to zero if no interaction
                bpm_value = 0
                update_status()  # Update the status to reflect no interaction

            time.sleep(0.1)
        except OSError:
            print("Heart Rate error, reinitializing...")
            time.sleep(1)

# OLED Display Thread with Compact Layout for 128x32 Display
def update_display():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)  # Compact font
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        with data_lock:
            # Create a blank image for drawing
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            
            # Display BPM value
            draw.text((0, 0), f"BPM: {bpm_value:.1f}", font=font, fill=255)
            
            # Draw BPM Graph beside BPM value
            if bpm_history:
                max_bpm = max(bpm_history) if max(bpm_history) > 0 else 1
                min_bpm = min(bpm_history)
                graph_height = 8
                graph_width = 60
                x_start = 50
                y_start = 0

                for i in range(1, len(bpm_history)):
                    y1 = y_start + graph_height - int((bpm_history[i-1] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    y2 = y_start + graph_height - int((bpm_history[i] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    x1 = x_start + (i - 1) * (graph_width // (len(bpm_history) - 1))
                    x2 = x_start + i * (graph_width // (len(bpm_history) - 1))
                    draw.line((x1, y1, x2, y2), fill=255, width=1)

            # Display LED Status and Human Interaction
            draw.text((0, 12), f"Status: {status}", font=font, fill=255)
            draw.text((0, 24), f"Interaction: {'Yes' if human_interaction else 'No'}", font=font, fill=255)

            # Update OLED display
            oled.image(image)
            oled.show()
        
        # Refresh to avoid blur
        time.sleep(1.5)

# Graceful exit for systemd service
def cleanup_and_exit(signum, frame):
    global running
    running = False
    set_leds_and_buzzer("Normal")  # Turn off all LEDs and buzzer on exit
    GPIO.cleanup()
    sys.exit(0)

# Main function to start threads for heart rate monitoring and display updating
if __name__ == "__main__":
    # Register signal handlers for graceful exit
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)
    
    try:
        heart_rate_thread = threading.Thread(target=monitor_heart_rate)
        display_thread = threading.Thread(target=update_display)
        
        heart_rate_thread.start()
        display_thread.start()

        heart_rate_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        print("Monitoring stopped.")
        cleanup_and_exit(None, None)