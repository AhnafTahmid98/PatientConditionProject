import smbus
import time

# I2C address of the ADS1115
ADS1115_ADDRESS = 0x48

# Register addresses for configuration and conversion
ADS1115_REG_CONVERT = 0x00
ADS1115_REG_CONFIG = 0x01

# Full-scale range (FSR) for the ADS1115 (2.048V)
FSR = 2.048
# The ADC is a 16-bit converter, so the maximum digital value is 32767
MAX_ADC_VALUE = 32767

# Initialize I2C (SMBus)
bus = smbus.SMBus(1)

# Function to configure and read a specific channel
def read_adc_channel(channel):
    # Configurations for the channel selection
    config = {
        0: 0xC300,  # A0
        1: 0xD300,  # A1
        2: 0xE300,  # A2
        3: 0xF300   # A3
    }
    if channel not in config:
        raise ValueError("Invalid channel. Choose from 0, 1, 2, or 3.")

    # Set up the configuration for the selected channel
    config_high = (config[channel] >> 8) & 0xFF
    config_low = config[channel] & 0xFF
    bus.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_REG_CONFIG, [config_high, config_low])

    # Wait for conversion to complete
    time.sleep(0.1)

    # Read the conversion result (2 bytes)
    data = bus.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_REG_CONVERT, 2)
    result = (data[0] << 8) | data[1]

    # Convert result to signed integer if necessary
    if result > 0x7FFF:
        result -= 0x10000

    return result

# Function to convert raw ADC value to voltage
def adc_to_voltage(adc_value):
    voltage = (adc_value / MAX_ADC_VALUE) * FSR
    return voltage

# Read and print the voltage of each channel
for channel in range(4):
    raw_value = read_adc_channel(channel)
    voltage = adc_to_voltage(raw_value)
    print(f"Channel {channel} voltage: {voltage:.4f} V")

# Close the I2C connection if necessary
bus.close()
