import time
import board
import busio
import threading
import asyncio
import websockets
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_mlx90614
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# Initialize the I2C bus and devices with a short delay for stability
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c)
mlx = adafruit_mlx90614.MLX90614(i2c)

# Initialize the OLED display (DFR0648)
WIDTH = 128
HEIGHT = 64
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

# Clear the display
oled.fill(0)
oled.show()

# Load default font
font = ImageFont.load_default()

# Moving average filter settings for GSR
window_size = 10  # Number of readings to average
readings = []

# Baseline and thresholds for GSR
baseline_value = 11000
contact_detection_threshold = 13000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

def read_gsr():
    # Read the analog value from channel 1 (A1)
    chan = AnalogIn(adc, 1)
    return chan.value

def get_moving_average(value):
    # Add the new reading to the list
    readings.append(value)
    
    # Keep only the last 'window_size' readings
    if len(readings) > window_size:
        readings.pop(0)
    
    # Calculate and return the average
    return sum(readings) / len(readings)

def determine_stress_level(smoothed_value):
    # Determine the stress level based on thresholds
    if smoothed_value < relaxed_threshold:
        return "Relaxed"
    elif relaxed_threshold <= smoothed_value < normal_threshold:
        return "Normal"
    elif normal_threshold <= smoothed_value < elevated_threshold:
        return "Elevated"
    else:
        return "High"

# Variables for heart rate monitoring
chan_hr = AnalogIn(adc, 0)  # Using channel A0 for heart rate
high_threshold = 2.5  # Example threshold values
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

async def monitor_heart_rate(websocket):
    global last_pulse_time, first_pulse
    while True:
        try:
            voltage = chan_hr.voltage
            if voltage > high_threshold and first_pulse:
                last_pulse_time = time.time()
                first_pulse = False
            elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
                pulse_interval = (time.time() - last_pulse_time) * 1000  # in ms
                last_pulse_time = time.time()
                bpm = 60000 / pulse_interval
                message = f"Heart Rate: {bpm:.2f} BPM"
                await websocket.send(message)
                display_message_on_oled(message)
            else:
                message = "Heart Rate: No human contact detected"
                await websocket.send(message)
                display_message_on_oled(message)

            time.sleep(0.1)
        except Exception as e:
            await websocket.send(f"Heart rate monitoring error: {e}")

async def monitor_temperature(websocket):
    while True:
        try:
            if readings and readings[-1] < contact_detection_threshold:
                ambient_temp = mlx.ambient_temperature
                object_temp = mlx.object_temperature
                message_ambient = f"Ambient Temp: {ambient_temp:.2f}°C"
                message_object = f"Object Temp: {object_temp:.2f}°C"
                await websocket.send(message_ambient)
                await websocket.send(message_object)
                display_message_on_oled(f"{message_ambient}\n{message_object}")
            else:
                message_ambient = "Ambient Temp: No human contact detected"
                message_object = "Object Temp: No human contact detected"
                await websocket.send(message_ambient)
                await websocket.send(message_object)
                display_message_on_oled(f"{message_ambient}\n{message_object}")

            time.sleep(3)
        except Exception as e:
            await websocket.send(f"Temperature monitoring error: {e}")

async def monitor_gsr(websocket):
    while True:
        try:
            gsr_value = read_gsr()
            smoothed_value = get_moving_average(gsr_value)
            if smoothed_value < contact_detection_threshold:
                contact_status = "Contact with human detected"
                stress_level = determine_stress_level(smoothed_value)
                message = f"Stress: {stress_level}"
                await websocket.send(message)
                display_message_on_oled(message)
            else:
                message = "Stress: No human contact detected"
                await websocket.send(message)
                display_message_on_oled(message)

            time.sleep(3)
        except Exception as e:
            await websocket.send(f"GSR monitoring error: {e}")

def display_message_on_oled(message):
    oled.fill(0)
    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), message, font=font, fill=255)
    oled.image(image)
    oled.show()

async def handler(websocket, path):
    await asyncio.gather(
        monitor_heart_rate(websocket),
        monitor_temperature(websocket),
        monitor_gsr(websocket)
    )

# Start the WebSocket server
start_server = websockets.serve(handler, "0.0.0.0", 8765)

# Run the server
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
