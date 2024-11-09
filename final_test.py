import os
import time
import board
import busio
import threading
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_mlx90614
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

# Load environment variables from .env file
load_dotenv()

# Retrieve email credentials from environment
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))

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

# Initialize LEDs and buzzer to OFF
GPIO.output(GREEN_LED, GPIO.LOW)
GPIO.output(YELLOW_LED, GPIO.LOW)
GPIO.output(RED_LED, GPIO.LOW)
GPIO.output(BUZZER_PIN, GPIO.LOW)

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
human_interaction = False
email_count = 0
email_sent_display = False

# Data lock
data_lock = threading.Lock()
running = True  # Flag to control threads

# Thresholds for GSR, BPM, and Temperature
BASELINE_VALUE = 11000
RELAXED_THRESHOLD = BASELINE_VALUE * 0.9
NORMAL_THRESHOLD = BASELINE_VALUE * 1.1
ELEVATED_THRESHOLD = BASELINE_VALUE * 1.3

# Heart rate thresholds and variables
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True
bpm_history = []  # For storing recent BPM values for graphing

# BPM thresholds for status levels
normal_bpm_range = (60, 100)
warning_bpm_range = (50, 120)

# Temperature thresholds
HUMAN_TEMP_RANGE = (35.8, 38.0)
HUMAN_TEMP_THRESHOLD_OFFSET = 2.5
MAX_ATTEMPTS = 3

# Function to send an email alert
def send_email_alert(status):
    global email_count, email_sent_display
    if email_count >= 5:
        return  # Limit to 5 emails

    try:
        subject = f"Health Alert: {status} Condition Detected"
        body = f"The health monitoring system has detected a {status} condition.\n\n"
        body += f"Current Readings:\n- BPM: {bpm_value}\n- Temperature: {temperature_value}°C\n- Stress Level: {stress_level}"

        # Set up the email message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = TO_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, TO_EMAIL, msg.as_string())
        email_count += 1
        email_sent_display = True
        print(f"Alert email sent for {status} condition.")

    except Exception as e:
        print(f"Failed to send email: {e}")

# Function to control LEDs and buzzer based on status and interaction status
def set_leds_and_buzzer(status, interaction):
    if status == "Normal":
        GPIO.output(GREEN_LED, GPIO.HIGH)
        GPIO.output(YELLOW_LED, GPIO.LOW)
        GPIO.output(RED_LED, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
    elif status == "Warning":
        GPIO.output(GREEN_LED, GPIO.LOW)
        GPIO.output(YELLOW_LED, GPIO.HIGH)
        GPIO.output(RED_LED, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
    elif status == "Critical" and interaction:
        GPIO.output(GREEN_LED, GPIO.LOW)
        GPIO.output(YELLOW_LED, GPIO.LOW)
        GPIO.output(RED_LED, GPIO.HIGH)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
    else:
        GPIO.output(GREEN_LED, GPIO.LOW)
        GPIO.output(YELLOW_LED, GPIO.LOW)
        GPIO.output(RED_LED, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)

# Update status based on BPM, GSR, and Temperature
def update_status():
    global status, email_count
    continuous_warning_or_critical = False

    if bpm_value < 50 or bpm_value > 120 or stress_level == "High" or temperature_value > 38:
        if status == "Critical":
            continuous_warning_or_critical = True
        status = "Critical"
    elif (50 <= bpm_value < 60 or 100 < bpm_value <= 120) or stress_level == "Elevated" or temperature_value > 37:
        if status == "Warning":
            continuous_warning_or_critical = True
        status = "Warning"
    else:
        status = "Normal"
        email_count = 0  # Reset email count on return to Normal

    if continuous_warning_or_critical:
        send_email_alert(status)

    set_leds_and_buzzer(status, human_interaction)

# GSR Monitoring
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

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

def monitor_gsr():
    global stress_level
    while running:
        try:
            gsr_value = read_gsr()
            stress_level = determine_stress_level(gsr_value)
            with data_lock:
                print(f"GSR Value: {gsr_value}, Stress Level: {stress_level}, Interaction: {human_interaction}")
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
            
            if voltage > high_threshold and first_pulse:
                last_pulse_time = current_time
                first_pulse = False
            elif voltage > high_threshold and (current_time - last_pulse_time) > 0.4:
                pulse_interval = (current_time - last_pulse_time) * 1000  # Convert to milliseconds
                bpm_value = 60000 / pulse_interval
                last_pulse_time = current_time

                with data_lock:
                    bpm_history.append(bpm_value)
                    if len(bpm_history) > 20:  # Limit history length
                        bpm_history.pop(0)
                    print(f"Heart Rate: {bpm_value:.2f} BPM")
                
                update_status()
            time.sleep(0.1)
        except OSError:
            print("Heart Rate error, reinitializing...")
            time.sleep(1)

# Temperature Monitoring
def get_stable_temperature(sensor, readings=20):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.02)
    return temp_sum / readings

def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

def monitor_temperature():
    global temperature_value, HUMAN_TEMP_THRESHOLD_OFFSET
    no_detection_count = 0
    while running:
        object_temp = get_stable_temperature(mlx)
        dynamic_threshold = get_dynamic_threshold(mlx.ambient_temperature)

        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
            temperature_value = object_temp
            with data_lock:
                print(f"Human Body Temperature: {temperature_value:.2f}°C")
            no_detection_count = 0
        else:
            no_detection_count += 1
            with data_lock:
                temperature_value = 0
                print("No human body detected.")

        if no_detection_count >= MAX_ATTEMPTS:
            HUMAN_TEMP_THRESHOLD_OFFSET += 0.1
            no_detection_count = 0
        time.sleep(1)

# OLED Display Thread with Compact Layout for 128x32 Display
def update_display():
    global email_sent_display  # Declare as global to avoid UnboundLocalError
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)  # Compact font
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        with data_lock:
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            draw.text((0, 0), f"BPM: {bpm_value:.1f}", font=font, fill=255)
            
            if bpm_history:
                max_bpm = max(bpm_history) if max(bpm_history) > 0 else 1
                min_bpm = min(bpm_history)
                graph_height = 8
                graph_width = 60
                x_start = 50
                y_start = 2

                for i in range(1, len(bpm_history)):
                    y1 = y_start + graph_height - int((bpm_history[i-1] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    y2 = y_start + graph_height - int((bpm_history[i] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    x1 = x_start + (i - 1) * (graph_width // (len(bpm_history) - 1))
                    x2 = x_start + i * (graph_width // (len(bpm_history) - 1))
                    draw.line((x1, y1, x2, y2), fill=255, width=1)

            draw.text((0, 12), f"Temp.: {temperature_value:.1f}C", font=font, fill=255)
            draw.text((0, 22), f"Stress: {stress_level}", font=font, fill=255)
            if email_sent_display:
                draw.text((80, 22), "Email Sent", font=font, fill=255)  # Display "Email Sent" on OLED

            oled.image(image)
            oled.show()
        
        email_sent_display = False  # Reset display flag after showing
        time.sleep(1.5)

# Main function
if __name__ == "__main__":
    try:
        # Start each monitoring thread
        gsr_thread = threading.Thread(target=monitor_gsr)
        heart_rate_thread = threading.Thread(target=monitor_heart_rate)
        temperature_thread = threading.Thread(target=monitor_temperature)
        display_thread = threading.Thread(target=update_display)

        # Start threads
        gsr_thread.start()
        heart_rate_thread.start()
        temperature_thread.start()
        display_thread.start()

        # Keep the main program running to allow threads to execute
        while running:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Monitoring stopped by user.")
        running = False  # Signal all threads to stop

    finally:
        # Wait for each thread to finish with a timeout
        gsr_thread.join(timeout=1)
        heart_rate_thread.join(timeout=1)
        temperature_thread.join(timeout=1)
        display_thread.join(timeout=1)

        # Cleanup GPIO and other resources
        set_leds_and_buzzer("Normal", False)
        GPIO.cleanup()
        print("All resources have been released and the program has exited cleanly.")
