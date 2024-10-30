try:
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn
    print("All modules imported successfully.")
except ImportError as e:
    print("ImportError:", e)
