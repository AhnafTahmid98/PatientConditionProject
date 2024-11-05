import time
import asyncio
import websockets
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import json

# Initialize I2C for OLED display and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
time.sleep(0.1)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)  # Using channel A0 for heart rate sensor

# Initialize OLED display
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.show()

# Load font for OLED display
try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12
    )
except IOError:
    font = ImageFont.load_default()

# Variables for pulse detection
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

# BPM data for graphing
bpm_data = []

# Function to update OLED display with BPM and plot graph
def update_oled_with_graph(bpm):
    if len(bpm_data) > 30:
        bpm_data.pop(0)
    bpm_data.append(bpm)

    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), f"BPM: {int(bpm)}", font=font, fill=255)

    if len(bpm_data) > 1:
        min_bpm, max_bpm = 50, 150
        scaled_data = [
            int(40 - 40 * (value - min_bpm) / (max_bpm - min_bpm))
            for value in bpm_data
        ]
        for i in range(1, len(scaled_data)):
            draw.line(
                [(i - 1) * 4, scaled_data[i - 1] + 20, i * 4, scaled_data[i] + 20],
                fill=255,
            )

    oled.image(image)
    oled.show()

# Async function to send BPM data over WebSocket and update OLED
async def send_bpm(websocket):
    global last_pulse_time, first_pulse

    while True:
        try:
            voltage = chan.voltage
            if voltage > high_threshold and first_pulse:
                last_pulse_time = time.time()
                first_pulse = False

            elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
                pulse_interval = (time.time() - last_pulse_time) * 1000
                last_pulse_time = time.time()
                bpm = 60000 / pulse_interval
                update_oled_with_graph(bpm)

                # Send both current BPM and the array of historical BPM data
                data = {'BPM': bpm, 'BPM_DATA': bpm_data}
                await websocket.send(json.dumps(data))

            await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(1)

# Main function to run the WebSocket server
async def main():
    async with websockets.serve(send_bpm, "0.0.0.0", 6789):
        await asyncio.Future()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")
