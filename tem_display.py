import time
import board
import busio
import threading
import signal
import sys
from adafruit_ads1x15.ads1115 import ADS1115
import adafruit_mlx90614
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

# Initialize I2C bus and sensors
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c, address=0x48)
mlx = adafruit_mlx90614.MLX90614(i2c, address=0x5a)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)

# Shared variables
temperature_value = 0
temperature_history = []  # Store recent temperature values for graphing
status = "Normal"

# Data lock for shared resources
data_lock = threading.Lock()
running = True

# Temperature threshold settings
HUMAN_TEMP_RANGE = (35.8, 40.0)  # Typical human body temperature range in °C
HUMAN_TEMP_THRESHOLD_OFFSET = 2.5
MAX_ATTEMPTS = 3

# Function to set LED and buzzer based on status
def set_leds_and_buzzer(status):
    GPIO.output(green_led, GPIO.HIGH if status == "Normal" else GPIO.LOW)
    GPIO.output(yellow_led, GPIO.HIGH if status == "Warning" else GPIO.LOW)
    GPIO.output(red_led, GPIO.HIGH if status == "Critical" else GPIO.LOW)
    GPIO.output(buzzer_pin, GPIO.HIGH if status == "Critical" else GPIO.LOW)

# Update status based on BPM value
def update_status():
    global status
    if temperature_value > 39:
        status = "Critical"
    elif temperature_value > 37.8:
        status = "Warning"
    else:
        status = "Normal"
    set_leds_and_buzzer(status)

# Function to dynamically adjust temperature threshold based on ambient temperature
def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

# Function to get stable temperature reading
def get_stable_temperature(sensor, readings=20):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.02)
    return temp_sum / readings

# Temperature monitoring function
def monitor_temperature():
    global temperature_value, status, HUMAN_TEMP_THRESHOLD_OFFSET
    no_detection_count = 0

    while running:
        object_temp = get_stable_temperature(mlx)
        dynamic_threshold = mlx.ambient_temperature + HUMAN_TEMP_THRESHOLD_OFFSET

        with data_lock:
            if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
                temperature_value = object_temp
                print(f"Human Body Temperature: {temperature_value:.2f}°C")
                # Write temperature to file for external reading
                with open("/home/pi/PatientConditionProject/temperature_data.txt", "w") as f:
                    f.write(f"{temperature_value:.3f}")

                # Append temperature value to history for graphing
                temperature_history.append(temperature_value)
                if len(temperature_history) > 20:  # Limit the history length
                    temperature_history.pop(0)
                no_detection_count = 0
            else:
                no_detection_count += 1
                temperature_value = 0
                print("No human body detected.")

            if no_detection_count >= MAX_ATTEMPTS:
                HUMAN_TEMP_THRESHOLD_OFFSET += 0.1
                no_detection_count = 0

        update_status()
        time.sleep(1)

# OLED Display function to show temperature and status
def update_display():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        with data_lock:
            # Create a blank image for drawing
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            
            # Display Temperature and Status
            draw.text((0, 0), f"Temp: {temperature_value:.1f}°C", font=font, fill=255)

            # Draw the temperature graph
            if temperature_history:
                max_temp = max(temperature_history) if max(temperature_history) > 0 else 1
                min_temp = min(temperature_history)
                graph_height = 8
                graph_width = 60
                x_start = 50
                y_start = 0

                for i in range(1, len(temperature_history)):
                    y1 = y_start + graph_height - int((temperature_history[i-1] - min_temp) / (max_temp - min_temp) * graph_height)
                    y2 = y_start + graph_height - int((temperature_history[i] - min_temp) / (max_temp - min_temp) * graph_height)
                    x1 = x_start + (i - 1) * (graph_width // (len(temperature_history) - 1))
                    x2 = x_start + i * (graph_width // (len(temperature_history) - 1))
                    draw.line((x1, y1, x2, y2), fill=255, width=1)

            draw.text((0, 16), f"Status: {status}", font=font, fill=255)

            # Update OLED display
            oled.image(image)
            oled.show()
        
        time.sleep(1.5)

# Graceful exit for systemd service
def cleanup_and_exit(signum, frame):
    global running
    running = False
    set_leds_and_buzzer("Normal")  # Turn off all LEDs and buzzer on exit
    GPIO.cleanup()
    sys.exit(0)

# Main function to start monitoring and display threads
if __name__ == "__main__":
    # Register signal handlers for graceful exit
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)
    
    try:
        temperature_thread = threading.Thread(target=monitor_temperature)
        display_thread = threading.Thread(target=update_display)
        
        temperature_thread.start()
        display_thread.start()

        temperature_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        cleanup_and_exit(None, None)