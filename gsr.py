import time
from Adafruit_ADS1x15 import ADS1115

# Initialize the ADS1115 (ADC)
adc = ADS1115()
GAIN = 1  # Gain setting for ADS1115

def read_gsr():
    # Read the analog value from channel 0 (SIG connected here)
    value = adc.read_adc(0, gain=GAIN)
    return value

try:
    while True:
        gsr_value = read_gsr()
        print("GSR Value:", gsr_value)
        
        # Delay for a bit
        time.sleep(1)

except KeyboardInterrupt:
    print("Program stopped.")
