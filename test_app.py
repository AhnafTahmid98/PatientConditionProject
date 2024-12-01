import time
import board
import busio
import threading
import signal
import sys
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_mlx90614
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

# Retrieve email credentials and server configuration from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  # Default SMTP port is 587
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("TO_EMAIL")

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

# Email tracking counters
email_sent_count = 0
MAX_EMAILS = 3
bpm_warning_count = 0
temp_warning_count = 0
stress_warning_count = 0

# Shared variables
bpm_value = 0
status = "Normal"
bpm_history = []  # For storing recent BPM values for graphing
temperature_value = 0
temperature_history = []  # Store recent temperature values for graphing
stress_level = "None"
human_interaction = False

# Heart rate thresholds and variables
high_threshold = 2.5  # Voltage thresholds for pulse detection
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

# BPM thresholds for status levels
normal_bpm_range = (60, 100)
warning_bpm_range = (50, 120)

# Temperature threshold settings
HUMAN_TEMP_RANGE = (35.8, 40.0)  # Typical human body temperature range in °C
HUMAN_TEMP_THRESHOLD_OFFSET = 2.5
MAX_ATTEMPTS = 3

# Thresholds for GSR
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3
GSR_AVERAGE_COUNT = 10  # Number of GSR readings to average for interaction check

# Flag to check if cleanup has already been done
cleaned_up = False

# Lock for synchronizing data access
data_lock = threading.Lock()
running = True

def send_email(subject, body):
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Log in to the email account
            server.send_message(msg)  # Send the email

        print(f"Email sent successfully to {RECIPIENT_EMAIL}.")
        """
        # Log email event for debugging
        with open("/home/pi/PatientConditionProject/email_log.txt", "a") as log:
            log.write(f"Email sent at {time.ctime()} - Subject: {subject}\n")
        """
        # Update the email sent flag
        with open("/home/pi/PatientConditionProject/email_sent_flag.txt", "w") as flag_file:
            flag_file.write("1")  # Write "1" to indicate an email was sent

    except Exception as e:
        print(f"Error sending email: {e}")

# Function to check conditions and send an email
def check_and_send_email():
    global email_sent_count, bpm_warning_count, temp_warning_count, stress_warning_count

    if email_sent_count < MAX_EMAILS:
        subject = "Health Monitoring Alert"
        details = []

        # Add specific messages for each out-of-range parameter
        if bpm_warning_count >= 2:
            details.append("BPM is out of range.")
        if temp_warning_count >= 2:
            details.append("Temperature is out of range.")
        if stress_warning_count >= 2:
            details.append("Stress Level is critical.")

        # Create a combined details message
        if len(details) == 1:
            detailed_message = details[0]
        elif len(details) == 2:
            detailed_message = f"Both {details[0][:-1]} and {details[1].lower()}"
        else:
            detailed_message = f"All parameters: {', '.join(details)}"

        body = (
            f"Health Alert!\n\n"
            f"Status: {status}\n"
            f"BPM: {bpm_value:.2f}\n"
            f"Temperature: {temperature_value:.2f}°C\n"
            f"Stress Level: {stress_level}\n\n"
            f"Details: {detailed_message}\n\n"
            f"Please take immediate action."
        )

        # Send email using send_email function
        send_email(subject, body)
        email_sent_count += 1
        print(f"Total emails sent so far: {email_sent_count}")  # Optional for tracking

        # Reset relevant counters to avoid duplicate emails for the same condition
        if bpm_warning_count >= 3:
            bpm_warning_count = 0
        if temp_warning_count >= 3:
            temp_warning_count = 0
        if stress_warning_count >= 3:
            stress_warning_count = 0
            
# Function to control LEDs and buzzer based on status and interaction status
def set_leds_and_buzzer(status, interaction):
    if interaction:  # Only trigger LEDs and buzzer if human interaction is detected
        if status == "Normal":
            GPIO.output(green_led, GPIO.HIGH)
            GPIO.output(yellow_led, GPIO.LOW)
            GPIO.output(red_led, GPIO.LOW)
            GPIO.output(buzzer_pin, GPIO.LOW)
        elif status == "Warning":
            GPIO.output(green_led, GPIO.LOW)
            GPIO.output(yellow_led, GPIO.HIGH)
            GPIO.output(red_led, GPIO.LOW)
            GPIO.output(buzzer_pin, GPIO.LOW)
        elif status == "Critical":
            GPIO.output(green_led, GPIO.LOW)
            GPIO.output(yellow_led, GPIO.LOW)
            GPIO.output(red_led, GPIO.HIGH)
            GPIO.output(buzzer_pin, GPIO.HIGH)
    else:
        # Turn off all LEDs and buzzer if there is no human interaction
        GPIO.output(green_led, GPIO.LOW)
        GPIO.output(yellow_led, GPIO.LOW)
        GPIO.output(red_led, GPIO.LOW)
        GPIO.output(buzzer_pin, GPIO.LOW)

# Update status based on BPM, GSR, and Temperature using ranges
def update_status():
    global status
    if human_interaction:
        # Status is "Critical" only if BPM, stress level, or temperature are out of range
        if bpm_value < warning_bpm_range[0] or bpm_value > warning_bpm_range[1] or stress_level == "High" or temperature_value > 39:
            status = "Critical"
        elif bpm_value < normal_bpm_range[0] or bpm_value > normal_bpm_range[1] or stress_level == "Elevated" or temperature_value > 38.7:
            status = "Warning"
        else:
            status = "Normal"
    else:
        # No human interaction: force "Normal" status
        status = "No Human Interaction"
    
    # Print status if it’s "Warning" or "Critical"
    if status != "Normal":
        print(f"Status: {status}, BPM: {bpm_value:.2f}, Temperature: {temperature_value:.2f}C, Stress Level: {stress_level}")
    
    set_leds_and_buzzer(status, human_interaction)

# Heart Rate Monitoring
def monitor_heart_rate():
    global bpm_value, bpm_history, last_pulse_time, first_pulse, running
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
                with open("/home/pi/PatientConditionProject/bpm_data.txt", "w") as f:
                    f.write(str(bpm_value))

                # Update status based on new BPM value
                update_status()
            time.sleep(0.1)
        except OSError:
            print("Heart Rate error, reinitializing...")
            time.sleep(1)

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
    global stress_level, human_interaction
    while running:
        try:
            # Average multiple GSR readings to confirm interaction
            gsr_readings = [read_gsr() for _ in range(GSR_AVERAGE_COUNT)]
            avg_gsr = sum(gsr_readings) / GSR_AVERAGE_COUNT
            stress_level = determine_stress_level(avg_gsr)
            with data_lock:
                print(f"GSR Avg: {avg_gsr:.2f}, Stress Level: {stress_level}, Interaction: {human_interaction}")
            with open("/home/pi/PatientConditionProject/gsr_data.txt", "w") as f:
                f.write(stress_level)
            time.sleep(3)
        except OSError:
            print("GSR error, reinitializing...")
            time.sleep(1)
            
# OLED Display Thread with Compact Layout for 128x32 Display
def update_display():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)  # Compact font
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        with data_lock:
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            draw.text((0, 0), f"BPM: {bpm_value:.1f}", font=font, fill=255)
            draw.text((0, 12), f"Temp.: {temperature_value:.1f}C", font=font, fill=255)
            draw.text((0, 22), f"Stress: {stress_level}", font=font, fill=255)
            
            oled.image(image)
            oled.show()
        
        time.sleep(1.5)

# Graceful exit for systemd service
def cleanup_and_exit(signum, frame):
    global running, cleaned_up
    if cleaned_up:  # If already cleaned up, return immediately
        return
    cleaned_up = True  # Set flag to indicate cleanup is done
    running = False
    print("Stop Measuring")  # Print statement for KeyboardInterrupt
    try:
        GPIO.output(green_led, GPIO.LOW)
        GPIO.output(yellow_led, GPIO.LOW)
        GPIO.output(red_led, GPIO.LOW)
        GPIO.output(buzzer_pin, GPIO.LOW)
        GPIO.cleanup()
    except RuntimeError:
        pass
    sys.exit(0)

# Main function to start monitoring and display threads
if __name__ == "__main__":
    # Register signal handlers for graceful exit
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

        heart_rate_thread.join()
        temperature_thread.join()
        gsr_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        cleanup_and_exit(None, None)