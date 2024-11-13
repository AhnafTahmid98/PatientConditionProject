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
import signal
import sys

# Load environment variables from .env file
load_dotenv()

# Email configurations
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))

# LED and buzzer setup
GREEN_LED, YELLOW_LED, RED_LED, BUZZER_PIN = 17, 27, 22, 23
GPIO.cleanup()
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

# Initialize I2C bus, sensors and oled display
i2c = busio.I2C(board.SCL, board.SDA)
adc, mlx = ADS1115(i2c, address=0x48), adafruit_mlx90614.MLX90614(i2c, address=0x5a)
adc.gain = 1
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)

# Shared variables and locks
bpm_value, temperature_value, stress_level = 0, 0, "None"
bpm_history, temperature_history = [], []
human_interaction, status, running = False, "Normal", True
data_lock = threading.Lock()

# Sensor thresholds
high_threshold, low_threshold = 2.5, 1.5
last_pulse_time, first_pulse = 0, True
normal_bpm_range, warning_bpm_range = (60, 100), (50, 120)
HUMAN_TEMP_RANGE, HUMAN_TEMP_THRESHOLD_OFFSET, MAX_ATTEMPTS = (35.8, 40.0), 2.5, 3
baseline_value, RELAXED_THRESHOLD = 11000, 11000 * 0.9
NORMAL_THRESHOLD, ELEVATED_THRESHOLD = baseline_value * 1.1, baseline_value * 1.3

# Counters for warning/critical statuses
consecutive_warning_with_human = 0
consecutive_critical_with_human = 0
required_consecutive_count = 5
email_count = 0
email_sent_display = False

# Function to send email alerts
def send_email_alert(status):
    global email_count, email_sent_display
    if email_count >= 5:
        return
    try:
        subject = f"Health Alert: {status} Condition Detected"
        body = f"Alert - {status} condition:\n- BPM: {bpm_value}\n- Temp: {temperature_value}°C\n- Stress: {stress_level}"
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = TO_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, TO_EMAIL, msg.as_string())
        
        email_count += 1
        email_sent_display = True
        print(f"Alert email sent for {status} condition.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Control LEDs and buzzer based on status and human interaction
def set_leds_and_buzzer(status, interaction):
    if status == "Normal" and interaction:
        GPIO.output(GREEN_LED, GPIO.HIGH)
        GPIO.output(YELLOW_LED, GPIO.LOW)
        GPIO.output(RED_LED, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
    elif status == "Warning" and interaction:
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

# Update status and trigger alerts if necessary
def update_status():
    global status, email_count, consecutive_warning_with_human, consecutive_critical_with_human
    human_present = human_interaction and temperature_value >= HUMAN_TEMP_RANGE[0]
    if human_present:
        if bpm_value < 50 or bpm_value > 120 or stress_level == "High" or temperature_value > 39:
            status = "Critical"
            consecutive_critical_with_human += 1
            consecutive_warning_with_human = 0
        elif (50 <= bpm_value < 60 or 100 < bpm_value <= 120) or stress_level == "Elevated" or temperature_value > 37.8:
            status = "Warning"
            consecutive_warning_with_human += 1
            consecutive_critical_with_human = 0
        else:
            status = "Normal"
            consecutive_critical_with_human = 0
            consecutive_warning_with_human = 0
            email_count = 0

        if status == "Critical" and consecutive_critical_with_human >= required_consecutive_count:
            send_email_alert(status)
            consecutive_critical_with_human = 0
        elif status == "Warning" and consecutive_warning_with_human >= required_consecutive_count:
            send_email_alert(status)
            consecutive_warning_with_human = 0

    set_leds_and_buzzer(status, human_interaction)

# Heart Rate Monitoring
def monitor_heart_rate():
    global bpm_value
    last_pulse_time = 0
    first_pulse = True
    while running:
        try:
            chan_heart_rate = AnalogIn(adc, 0)
            voltage = chan_heart_rate.voltage
            current_time = time.time()
            if voltage > high_threshold and first_pulse:
                last_pulse_time = current_time
                first_pulse = False
            elif voltage > high_threshold and (current_time - last_pulse_time) > 0.4:
                pulse_interval = (current_time - last_pulse_time) * 1000
                bpm_value = 60000 / pulse_interval
                last_pulse_time = current_time
                update_status()
            time.sleep(0.1)
        except OSError:
            time.sleep(1)

# Function to get a stable temperature reading by averaging multiple readings
def get_stable_temperature(sensor, readings=20):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.02)  # Small delay between readings
    return temp_sum / readings

# Function to calculate the dynamic temperature threshold based on ambient temperature
def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

# Temperature Monitoring
def monitor_temperature():
    global temperature_value, HUMAN_TEMP_THRESHOLD_OFFSET
    no_detection_count = 0
    while running:
        try:
            object_temp = get_stable_temperature(mlx)
            dynamic_threshold = get_dynamic_threshold(mlx.ambient_temperature)
            if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
                temperature_value = object_temp
                no_detection_count = 0
            else:
                no_detection_count += 1
                temperature_value = 0

            if no_detection_count >= MAX_ATTEMPTS:
                HUMAN_TEMP_THRESHOLD_OFFSET += 0.1
                no_detection_count = 0
            update_status()
            time.sleep(1)
        except Exception as e:
            time.sleep(1)

# GSR Monitoring
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

def determine_stress_level(gsr_value):
    global human_interaction
    if gsr_value < 13000:  # Threshold for human interaction
        human_interaction = True
        if gsr_value < RELAXED_THRESHOLD:
            return "Relaxed"
        elif gsr_value < NORMAL_THRESHOLD:
            return "Normal"
        elif gsr_value < ELEVATED_THRESHOLD:
            return "Elevated"
        else:
            return "High"
    else:
        human_interaction = False
        return "NO-CONTACT"

def monitor_gsr():
    global stress_level
    while running:
        try:
            gsr_value = read_gsr()
            stress_level = determine_stress_level(gsr_value)
            update_status()
            time.sleep(3)
        except OSError:
            time.sleep(1)

# OLED Display
def update_display():
    global email_sent_display
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        try:
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            draw.text((0, 0), f"BPM: {bpm_value:.1f}", fill=255)
            draw.text((0, 12), f"Temp: {temperature_value:.1f}°C", fill=255)
            draw.text((0, 22), f"Stress: {stress_level}", fill=255)
            if email_sent_display:
                draw.text((80, 22), "Email Sent", fill=255)
            oled.image(image)
            oled.show()
            email_sent_display = False
            time.sleep(1.5)
        except Exception as e:
            time.sleep(1)

# Graceful exit function
def cleanup_and_exit(signum, frame):
    global running
    running = False
    GPIO.setmode(GPIO.BCM)  # Set pin numbering mode if needed

    # Turn off LEDs and buzzer
    GPIO.output(GREEN_LED, GPIO.LOW)
    GPIO.output(YELLOW_LED, GPIO.LOW)
    GPIO.output(RED_LED, GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    
    print("Exiting gracefully.")
    time.sleep(1)  # Small delay to ensure threads exit

# Main function
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    try:
        heart_rate_thread = threading.Thread(target=monitor_heart_rate)
        temperature_thread = threading.Thread(target=monitor_temperature)
        gsr_thread = threading.Thread(target=monitor_gsr)
        display_thread = threading.Thread(target=update_display)

        heart_rate_thread.start()
        temperature_thread.start()
        gsr_thread.start()
        display_thread.start()

        # Join threads to ensure all threads exit gracefully
        heart_rate_thread.join()
        temperature_thread.join()
        gsr_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        cleanup_and_exit(None, None)