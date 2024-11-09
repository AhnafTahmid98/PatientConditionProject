import os
import time
import board
import busio
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
from multiprocessing import Process, Manager

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

# Shared variables using Manager
manager = Manager()
shared_data = manager.dict()
shared_data["bpm_value"] = 0
shared_data["temperature_value"] = 0
shared_data["stress_level"] = "None"
shared_data["status"] = "Normal"
shared_data["human_interaction"] = False
shared_data["email_count"] = 0
shared_data["email_sent_display"] = False
shared_data["running"] = True  # Monitoring flag, controlled by commands from app

# Initialize display_queue and email_sent_display for display updates
display_queue = manager.Queue()
email_sent_display = manager.Value('b', False)

# Thresholds and Variables for GSR
BASELINE_VALUE = 11000
RELAXED_THRESHOLD = BASELINE_VALUE * 0.9
NORMAL_THRESHOLD = BASELINE_VALUE * 1.1
ELEVATED_THRESHOLD = BASELINE_VALUE * 1.3

# Heart rate thresholds and variables
high_threshold = 2.5
low_threshold = 1.5

# BPM thresholds for status levels
normal_bpm_range = (60, 100)
warning_bpm_range = (50, 120)

# Temperature thresholds
HUMAN_TEMP_RANGE = (35.8, 40.0)
HUMAN_TEMP_THRESHOLD_OFFSET = 2.5
MAX_ATTEMPTS = 3

# Function to send an email alert
def send_email_alert(status, shared_data):
    if shared_data["email_count"] >= 5:
        return  # Limit to 5 emails

    try:
        subject = f"Health Alert: {status} Condition Detected"
        body = f"The health monitoring system has detected a {status} condition.\n\n"
        body += f"Current Readings:\n- BPM: {shared_data['bpm_value']}\n- Temperature: {shared_data['temperature_value']}°C\n- Stress Level: {shared_data['stress_level']}"

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
        
        shared_data["email_count"] += 1
        email_sent_display.value = True  # Set flag to show "Email Sent" on OLED display
        print(f"Alert email sent for {status} condition.")

    except Exception as e:
        print(f"Failed to send email: {e}")

# Function to control LEDs and buzzer based on status
def set_leds_and_buzzer(status, interaction, shared_data):
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
def update_status(shared_data):
    human_present = shared_data["human_interaction"] and shared_data["temperature_value"] >= HUMAN_TEMP_RANGE[0]
    if human_present:
        if shared_data["bpm_value"] < 50 or shared_data["bpm_value"] > 120 or shared_data["stress_level"] == "High" or shared_data["temperature_value"] > 39:
            shared_data["status"] = "Critical"
        elif (50 <= shared_data["bpm_value"] < 60 or 100 < shared_data["bpm_value"] <= 120) or shared_data["stress_level"] == "Elevated" or shared_data["temperature_value"] > 37.8:
            shared_data["status"] = "Warning"
        else:
            shared_data["status"] = "Normal"
            shared_data["email_count"] = 0  # Reset email count on return to Normal

        # Trigger email alerts
        if shared_data["status"] == "Critical":
            send_email_alert("Critical", shared_data)
        elif shared_data["status"] == "Warning":
            send_email_alert("Warning", shared_data)

    # Update LEDs and buzzer
    set_leds_and_buzzer(shared_data["status"], shared_data["human_interaction"], shared_data)

# GSR Monitoring
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

def determine_stress_level(gsr_value, shared_data):
    if gsr_value < 13000:
        shared_data["human_interaction"] = True
        if gsr_value < RELAXED_THRESHOLD:
            return "Normal"
        elif gsr_value < NORMAL_THRESHOLD:
            return "Normal"
        elif gsr_value < ELEVATED_THRESHOLD:
            return "Elevated"
        else:
            return "High"
    else:
        shared_data["human_interaction"] = False
        return "No-contact"

def monitor_gsr(shared_data):
    while shared_data["running"]:
        try:
            gsr_value = read_gsr()
            shared_data["stress_level"] = determine_stress_level(gsr_value, shared_data)
            display_queue.put((shared_data["bpm_value"], shared_data["temperature_value"], shared_data["stress_level"]))  # Send to display
            print(f"GSR Value: {gsr_value}, Stress Level: {shared_data['stress_level']}, Interaction: {shared_data['human_interaction']}")
            update_status(shared_data)
            time.sleep(3)
        except OSError:
            print("GSR error, reinitializing...")
            time.sleep(1)

# Heart Rate Monitoring
def monitor_heart_rate(shared_data):
    last_pulse_time = time.time()
    first_pulse = True
    while shared_data["running"]:
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

                shared_data["bpm_value"] = bpm_value
                print(f"Heart Rate: {bpm_value:.2f} BPM")
                display_queue.put((shared_data["bpm_value"], shared_data["temperature_value"], shared_data["stress_level"]))  # Send to display
                
                update_status(shared_data)
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

def monitor_temperature(shared_data):
    no_detection_count = 0
    while shared_data["running"]:
        object_temp = get_stable_temperature(mlx)
        dynamic_threshold = get_dynamic_threshold(mlx.ambient_temperature)

        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
            shared_data["temperature_value"] = object_temp
            display_queue.put((shared_data["bpm_value"], shared_data["temperature_value"], shared_data["stress_level"]))  # Send to display
            print(f"Human Body Temperature: {object_temp:.2f}°C")
            no_detection_count = 0
        else:
            no_detection_count += 1
            shared_data["temperature_value"] = 0
            print("No human body detected.")

        if no_detection_count >= MAX_ATTEMPTS:
            HUMAN_TEMP_THRESHOLD_OFFSET += 0.1
            no_detection_count = 0
        update_status(shared_data)
        time.sleep(1)

# OLED Display Update Process
def update_display(display_queue, email_sent_display, running):
    bpm_history = []  # For storing recent BPM values for graphing

    while running.value:
        while not display_queue.empty():
            bpm_value, temperature_value, stress_level = display_queue.get()
            
            # Add the current BPM to history, maintaining a max length of 20 entries
            bpm_history.append(bpm_value)
            if len(bpm_history) > 20:
                bpm_history.pop(0)

            # Create an image to draw on the OLED display
            font = ImageFont.load_default()
            image = Image.new("1", (128, 32))
            draw = ImageDraw.Draw(image)
            draw.text((0, 0), f"BPM: {bpm_value}", font=font, fill=255)
            
            # Draw BPM graph if bpm_history has values
            if bpm_history:
                max_bpm = max(bpm_history) if max(bpm_history) > 0 else 1
                min_bpm = min(bpm_history)
                graph_height = 8
                graph_width = 60
                x_start = 50
                y_start = 2

                for i in range(1, len(bpm_history)):
                    y1 = y_start + graph_height - int((bpm_history[i - 1] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    y2 = y_start + graph_height - int((bpm_history[i] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    x1 = x_start + (i - 1) * (graph_width // (len(bpm_history) - 1))
                    x2 = x_start + i * (graph_width // (len(bpm_history) - 1))
                    draw.line((x1, y1, x2, y2), fill=255, width=1)
            
            draw.text((0, 12), f"Temp.: {temperature_value}C", font=font, fill=255)
            draw.text((0, 24), f"Stress: {stress_level}", font=font, fill=255)
            
            # Display "Email Sent" message if applicable
            if email_sent_display.value:
                draw.text((90, 24), "Email Sent", font=font, fill=255)
                email_sent_display.value = False  # Reset display flag after showing

            # Send the drawn image to the OLED display
            oled.image(image)
            oled.show()
        
        time.sleep(1)  # Update rate for the display

# WebSocket Server Handler
async def websocket_handler(websocket, path, shared_data):
    while shared_data["running"]:
        data = {
            "bpm": shared_data["bpm_value"],
            "temperature": shared_data["temperature_value"],
            "stress_level": shared_data["stress_level"]
        }
        await websocket.send(json.dumps(data))
        await asyncio.sleep(1)

def start_websocket_server(shared_data):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = websockets.serve(lambda ws, path: websocket_handler(ws, path, shared_data), "0.0.0.0", 8765)
    loop.run_until_complete(server)
    loop.run_forever()

# Main function
if __name__ == "__main__":
    shared_data["running"] = manager.Value('b', True)  # For graceful exit

    # Start multiprocessing processes
    processes = [
        Process(target=start_websocket_server, args=(shared_data,)),
        Process(target=monitor_gsr, args=(shared_data,)),
        Process(target=monitor_heart_rate, args=(shared_data,)),
        Process(target=monitor_temperature, args=(shared_data,)),
        Process(target=update_display, args=(display_queue, email_sent_display, shared_data["running"])),
    ]

    for process in processes:
        process.start()

    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        shared_data["running"].value = False
        for process in processes:
            process.terminate()
        GPIO.cleanup()  # Cleanup GPIO
