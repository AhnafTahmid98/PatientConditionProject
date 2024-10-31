import time
import asyncio
import websockets
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio

# Setup I2C communication and initialize the ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)  # Using channel A0 directly

# Variables for pulse detection
high_threshold = 2.5  # Example threshold values
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

async def send_bpm(websocket):
    global last_pulse_time, first_pulse
    print("Starting heart rate measurement on A0...")

    while True:
        voltage = chan.voltage
        print(f"Voltage on A0: {voltage:.3f} V")

        if voltage > high_threshold and first_pulse:
            print("Pulse detected (first pulse)")
            last_pulse_time = time.time()
            first_pulse = False

        elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
            pulse_interval = (time.time() - last_pulse_time) * 1000  # in ms
            last_pulse_time = time.time()
            bpm = 60000 / pulse_interval
            print(f"Pulse detected. Interval: {pulse_interval:.2f} ms")
            print(f"Heart Rate: {bpm:.2f} BPM")

            # Send BPM data to WebSocket client
            await websocket.send(str(bpm))

        await asyncio.sleep(0.1)

async def main():
    async with websockets.serve(send_bpm, "0.0.0.0", 6789):  # Replace with Pi IP
        await asyncio.Future()  # Run forever

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")
