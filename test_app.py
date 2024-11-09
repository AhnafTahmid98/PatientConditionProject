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
import asyncio
import websockets
import json

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

# Clean up GPIO before setting up
GPIO.cleanup()

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

# Flags for control
running = True  # Controls the monitoring threads
websocket_running = False  # Controls WebSocket data transmission

# Global variable to store the monitoring task- websocket
monitoring_task = None

# Data lock
data_lock = threading.Lock()

# Heart rate thresholds and variables
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True
bpm_history = []  # For storing recent BPM values for graphing

# BPM thresholds for status levels
normal_bpm_range = (60, 100)
warning_bpm_range = (50, 120)

# Thresholds and Variables for GSR
BASELINE_VALUE = 11000
RELAXED_THRESHOLD = BASELINE_VALUE * 0.9
NORMAL_THRESHOLD = BASELINE_VALUE * 1.1
ELEVATED_THRESHOLD = BASELINE_VALUE * 1.3

# Thresholds and Variables for Temperature
HUMAN_TEMP_RANGE = (35.8, 40.0)
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

# Function to control LEDs and buzzer based on status
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

# Update status based on BPM, GSR, and Temperature, and check for human presence
def update_status():
    global status, email_count, consecutive_warning_with_human, consecutive_critical_with_human

    # Check human presence and update status
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
            email_count = 0  # Reset email count on return to Normal

        # Only send email if threshold count is met for human-related warning or critical status
        if status == "Critical" and consecutive_critical_with_human >= required_consecutive_count:
            send_email_alert(status)
            consecutive_critical_with_human = 0
        elif status == "Warning" and consecutive_warning_with_human >= required_consecutive_count:
            send_email_alert(status)
            consecutive_warning_with_human = 0

    # Ensure LEDs and buzzer reflect current status
    set_leds_and_buzzer(status, human_interaction)

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

                bpm_history.append(bpm_value)
                if len(bpm_history) > 20:
                    bpm_history.pop(0)
                print(f"Heart Rate: {bpm_value:.2f} BPM")
                
                update_status()
            time.sleep(0.1)
        except OSError:
            print("Heart Rate error, reinitializing...")
            time.sleep(1)
        except Exception as e:
            print(f"Unexpected error in heart rate monitoring: {e}")
            time.sleep(1)

# GSR Monitoring
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

def determine_stress_level(gsr_value):
    global human_interaction
    if gsr_value < 13000:
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
        return "No-contact"

def monitor_gsr():
    global stress_level
    while running:
        try:
            gsr_value = read_gsr()
            stress_level = determine_stress_level(gsr_value)
            print(f"GSR Value: {gsr_value}, Stress Level: {stress_level}, Interaction: {human_interaction}")
            update_status()
            time.sleep(3)
        except OSError:
            print("GSR error, reinitializing...")
            time.sleep(1)
        except Exception as e:
            print(f"Unexpected error in GSR monitoring: {e}")
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
            object_temp = get_stable_temperature(mlx)  # Call the defined function
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
        except Exception as e:
            print(f"Unexpected error in temperature monitoring: {e}")
            time.sleep(1)
        
# OLED Display Thread
def update_display():
    global email_sent_display
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 9)
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        try:
            with data_lock:
                image = Image.new("1", (128, 32))
                draw = ImageDraw.Draw(image)
                draw.text((0, 0), f"BPM: {bpm_value:.1f}", font=font, fill=255)
                draw.text((0, 12), f"Temp.: {temperature_value:.1f}C", font=font, fill=255)
                draw.text((0, 22), f"Stress: {stress_level}", font=font, fill=255)
                if email_sent_display:
                    draw.text((80, 22), "Email Sent", font=font, fill=255)

                oled.image(image)
                oled.show()
            
            email_sent_display = False
            time.sleep(1.5)
        except Exception as e:
            print(f"Unexpected error in OLED display: {e}")
            time.sleep(1)

# WebSocket Handler
async def websocket_handler(websocket, _):
    global websocket_running, monitoring_task

    async def send_data():
        while websocket_running:
            data = {
                "bpm": bpm_value,
                "temperature": temperature_value,
                "stress_level": stress_level
            }
            await websocket.send(json.dumps(data))
            await asyncio.sleep(1)

    async for message in websocket:
        command = json.loads(message).get("command")
        if command == "START_MONITORING":
            if not websocket_running:
                websocket_running = True
                await websocket.send(json.dumps({"status": "Monitoring started"}))
                monitoring_task = asyncio.create_task(send_data())
        elif command == "STOP_MONITORING":
            if websocket_running:
                websocket_running = False
                await websocket.send(json.dumps({"status": "Monitoring stopped"}))
                if monitoring_task:
                    monitoring_task.cancel()
                    monitoring_task = None
            
# Start WebSocket Server
def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = websockets.serve(websocket_handler, "0.0.0.0", 8765)
    loop.run_until_complete(server)
    loop.run_forever()

# Main function
if __name__ == "__main__":
    try:
        websocket_thread = threading.Thread(target=start_websocket_server)
        websocket_thread.start()

        heart_rate_thread = threading.Thread(target=monitor_heart_rate)
        gsr_thread = threading.Thread(target=monitor_gsr)
        temperature_thread = threading.Thread(target=monitor_temperature)
        display_thread = threading.Thread(target=update_display)

        heart_rate_thread.start()
        gsr_thread.start()
        temperature_thread.start()
        display_thread.start()

        heart_rate_thread.join()
        gsr_thread.join()
        temperature_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        print("Monitoring stopped.")
    finally:
        running = False
        set_leds_and_buzzer("Normal", False)
        GPIO.cleanup()
        print("Cleaned up resources.")
