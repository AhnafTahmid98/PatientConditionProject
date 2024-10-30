import time
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS1115

# Initialize I2C bus and ADS1115 for heart rate sensor
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)

# Heart rate calculation variables
counter = 0
temp = [0] * 21
max_heartpulse_duty = 2000  # 2 seconds as the maximum allowed time between pulses
data_effect = True
heart_rate = 0

def array_init():
    """Initialize the array for pulse timestamps."""
    global temp
    for i in range(20):
        temp[i] = 0
    temp[20] = int(time.time() * 1000)  # Record the current time in milliseconds

def calculate_heart_rate():
    """Calculate heart rate based on the last 20 pulses."""
    global heart_rate, data_effect
    if data_effect:
        # Calculate BPM as 60 * 20 / total_time for 20 pulses
        heart_rate = 1200000 // (temp[20] - temp[0])
        print(f"Heart Rate: {heart_rate} BPM")
    data_effect = True

def check_pulse():
    """Check for a pulse by reading sensor voltage and calculate BPM if a pulse is detected."""
    global counter, temp, data_effect

    # Read voltage from the sensor
    voltage = chan.voltage

    # Detect a pulse when voltage goes above threshold
    if voltage > 2.0:  # Adjust threshold based on your sensor's baseline output
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        temp[counter] = current_time
        
        # Debugging output for tracking pulse intervals
        print(f"Pulse detected at index {counter}, Time: {temp[counter]} ms")

        # Calculate the interval between this and the previous pulse
        if counter == 0:
            sub = temp[counter] - temp[20]
        else:
            sub = temp[counter] - temp[counter - 1]

        print(f"Interval since last pulse: {sub} ms")

        # Check if the interval is within an acceptable range
        if sub > max_heartpulse_duty:
            data_effect = False
            counter = 0
            print("Heart rate measure error, restarting measurement.")
            array_init()  # Re-initialize if pulse interval is too long
        elif counter == 20 and data_effect:
            counter = 0
            calculate_heart_rate()  # Calculate BPM after 20 pulses
        elif counter != 20 and data_effect:
            counter += 1
        else:
            counter = 0
            data_effect = True

# Main loop
try:
    print("Starting heart rate measurement...")
    array_init()
    while True:
        check_pulse()
        time.sleep(0.05)  # Small delay to reduce CPU usage

except KeyboardInterrupt:
    print("Measurement stopped by user.")
