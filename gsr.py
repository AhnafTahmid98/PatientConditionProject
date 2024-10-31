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

# Baseline and thresholds (adjust based on your observed baseline)
baseline_value = 11000
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

try:
    while True:
        gsr_value = read_gsr()
        smoothed_value = get_moving_average(gsr_value)
        
        # Determine contact status
        if smoothed_value < 13000:
            contact_status = "Contact with human detected"
            stress_level = determine_stress_level(smoothed_value)
            print(f"{contact_status} | Stress Level: {stress_level} | Smoothed GSR Value: {smoothed_value}")
        else:
            print("No contact detected")
        
        # Delay for a bit to observe changes over time
        time.sleep(1)

except KeyboardInterrupt:
    print("Program stopped.")
