import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Set up I2C and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c)
adc.gain = 1  # Set gain for ADC

# Moving average filter settings
window_size = 10  # Number of readings to average
readings = []

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

try:
    while True:
        gsr_value = read_gsr()
        smoothed_value = get_moving_average(gsr_value)
        print(f"Raw GSR Value: {gsr_value} | Smoothed GSR Value: {smoothed_value}")
        
        # Delay for a bit to observe changes over time
        time.sleep(1)

except KeyboardInterrupt:
    print("Program stopped.")
