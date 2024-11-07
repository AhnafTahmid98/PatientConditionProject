import time
import board
import busio
import threading
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_mlx90614
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

# LED and buzzer pin definitions
green_led = 17  # GPIO 17
yellow_led = 27  # GPIO 27
red_led = 22  # GPIO 22
buzzer_pin = 23  # GPIO 23

# GPIO setup for LEDs and buzzer
GPIO.setmode(GPIO.BCM)
GPIO.setup(green_led, GPIO.OUT)
GPIO.setup(yellow_led, GPIO.OUT)
GPIO.setup(red_led, GPIO.OUT)
GPIO.setup(buzzer_pin, GPIO.OUT)

# Initialize I2C bus and sensors
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c, address=0x48)
adc.gain = 1
mlx = adafruit_mlx90614.MLX90614(i2c, address=0x5a)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)

# Shared variables
bpm_value = 0
temperature_value = 0
stress_level = "None"
status = "Normal"

# Data lock
data_lock = threading.Lock()
running = True  # Flag to control threads

# Thresholds for GSR, BPM, and Temperature
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

# Heart rate and temperature thresholds for alert levels
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True
bpm_history = []  # For storing recent BPM values for graphing

normal_bpm_range = (60, 100)  # Normal BPM range for adults

# Functions to control LEDs and buzzer
def set_leds_and_buzzer(state):
    GPIO.output(green_led, GPIO.HIGH if state == "Normal" else GPIO.LOW)
    GPIO.output(yellow_led, GPIO.HIGH if state == "Warning" else GPIO.LOW)
    GPIO.output(red_led, GPIO.HIGH if state == "Critical" else GPIO.LOW)
    GPIO.output(buzzer_pin, GPIO.HIGH if state == "Critical" else GPIO.LOW)

# GSR Functions
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

def determine_stress_level(value):
    if value < relaxed_threshold:
        return "Normal"
    elif value < normal_threshold:
        return "Normal"
    elif value < elevated_threshold:
        return "Elevated"
    else:
        return "High"

# Monitor GSR
def monitor_gsr():
    global stress_level, status
    while running:
        try:
            gsr_value = read_gsr()
            stress_level = determine_stress_level(gsr_value)
            with data_lock:
                print(f"Stress Level: {stress_level} | GSR Value: {gsr_value}")
            update_status()
            time.sleep(3)
        except OSError:
            print("GSR error, reinitializing...")
            time.sleep(1)

# Heart Rate Monitoring
def monitor_heart_rate():
    global bpm_value, last_pulse_time, first_pulse, bpm_history
    while running:
        try:
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
            time.sleep(0.1)
        except OSError:
            print("Heart Rate error, reinitializing...")
            time.sleep(1)

# Monitor Temperature
def monitor_temperature():
    global temperature_value
    while running:
        try:
            temperature_value = mlx.object_temperature
            with data_lock:
                print(f"Temperature: {temperature_value:.2f}°C")
            update_status()
            time.sleep(1)
        except OSError:
            print("Temperature error, reinitializing...")
            time.sleep(1)

# Determine overall status based on BPM, GSR, and Temperature
def update_status():
    global status
    if bpm_value < normal_bpm_range[0] or bpm_value > normal_bpm_range[1] or \
       stress_level == "High" or temperature_value > 38:
        status = "Critical"
    elif stress_level == "Elevated" or temperature_value > 37:
        status = "Warning"
    else:
        status = "Normal"
    set_leds_and_buzzer(status)

# OLED Display Thread
def update_display():
    font = ImageFont.load_default()
    while running:
        with data_lock:
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            
            # Display BPM
            draw.text((0, 0), f"BPM: {bpm_value:.1f}", font=font, fill=255)
            
            # Display Temperature
            draw.text((0, 12), f"Temp: {temperature_value:.1f}°C", font=font, fill=255)
            
            # Display Stress Level
            draw.text((0, 24), f"Stress: {stress_level}", font=font, fill=255)
            
            # Draw BPM history graph if available
            if bpm_history:
                max_bpm = max(bpm_history) if max(bpm_history) > 0 else 1
                min_bpm = min(bpm_history)
                graph_height = 8
                graph_width = 60
                x_start = 70
                y_start = 0

                for i in range(1, len(bpm_history)):
                    y1 = y_start + graph_height - int((bpm_history[i-1] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    y2 = y_start + graph_height - int((bpm_history[i] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    x1 = x_start + (i - 1) * (graph_width // (len(bpm_history) - 1))
                    x2 = x_start + i * (graph_width // (len(bpm_history) - 1))
                    draw.line((x1, y1, x2, y2), fill=255, width=1)

            oled.image(image)
            oled.show()
        time.sleep(1.5)

# Main function
if __name__ == "__main__":
    try:
        # Start threads for monitoring and displaying data
        gsr_thread = threading.Thread(target=monitor_gsr)
        heart_rate_thread = threading.Thread(target=monitor_heart_rate)
        temperature_thread = threading.Thread(target=monitor_temperature)
        display_thread = threading.Thread(target=update_display)
        
        gsr_thread.start()
        heart_rate_thread.start()
        temperature_thread.start()
        display_thread.start()

        gsr_thread.join()
        heart_rate_thread.join()
        temperature_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        print("Monitoring stopped.")
        running = False
        set_leds_and_buzzer("Normal")  # Turn off all LEDs and buzzer on exit
        GPIO.cleanup()
