import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Set up I2C and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS1115(i2c)
adc.gain = 1  # Set gain for ADC

def read_gsr():
    # Read the analog value from channel 1 (A1)
    chan = AnalogIn(adc, 1)
    return chan.value

try:
    while True:
        gsr_value = read_gsr()
        print("GSR Value:", gsr_value)
        
        # Delay for a bit to observe changes over time
        time.sleep(1)

except KeyboardInterrupt:
    print("Program stopped.")
