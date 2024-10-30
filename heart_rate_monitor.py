try:
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.ads import ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    print("ADS library imported successfully.")
except ImportError as e:
    print(f"Import error: {e}")
