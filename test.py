import time
import board
import busio
import threading
import adafruit_mlx90614
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize the I2C bus and devices with a short delay for stability
def initialize_ads():
    i2c_ads = busio.I2C(board.SCL, board.SDA)
    time.sleep(0.5)  # Short delay to stabilize the I2C bus
    adc = ADS1115(i2c_ads)
    adc.gain = 1
    return adc

# Initialize the MLX90614 temperature sensor
def initialize_mlx():
    i2c_temp = busio.I2C(board.SCL, board.SDA)
    mlx = adafruit_mlx90614.MLX90614(i2c_temp)
    return mlx

# Set up initial I2C devices
adc = initialize_ads()
mlx = initialize_mlx()

# Moving average filter settings for GSR
window_size = 10  # Number of readings to average
readings = []

# Baseline and thresholds for GSR
baseline_value = 11000
contact_detection_threshold = 13000
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

# Variables for heart rate monitoring
chan_hr = AnalogIn(adc, 0)  # Using channel A0 for heart rate
high_threshold = 2.5  # Example threshold values
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

def monitor_heart_rate():
    global last_pulse_time, first_pulse
    while True:
        try:
            # Read heart rate data
            voltage = chan_hr.voltage
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

            time.sleep(0.1)
        except Exception as e:
            print(f"Heart rate monitoring error: {e}")

def monitor_temperature():
    while True:
        try:
            # Only read temperature if contact is detected by GSR
            if readings and readings[-1] < contact_detection_threshold:
                ambient_temp = mlx.ambient_temperature
                object_temp = mlx.object_temperature
                print(f"Ambient Temperature: {ambient_temp:.2f}°C")
                print(f"Object Temperature: {object_temp:.2f}°C")
            else:
                print("No human contact detected (temperature)")
            
            time.sleep(3)
        except Exception as e:
            print(f"Temperature monitoring error: {e}")

def monitor_gsr():
    while True:
        try:
            gsr_value = read_gsr()
            smoothed_value = get_moving_average(gsr_value)

            # Check for human contact before processing other sensor data
            if smoothed_value < contact_detection_threshold:
                contact_status = "Contact with human detected"
                stress_level = determine_stress_level(smoothed_value)
                print(f"{contact_status} | Stress Level: {stress_level} | Smoothed GSR Value: {smoothed_value}")
            else:
                print("No human contact detected (GSR)")
            
            time.sleep(3)
        except Exception as e:
            print(f"GSR monitoring error: {e}")

# Create and start threads for simultaneous monitoring
heart_rate_thread = threading.Thread(target=monitor_heart_rate)
temperature_thread = threading.Thread(target=monitor_temperature)
gsr_thread = threading.Thread(target=monitor_gsr)

heart_rate_thread.start()
temperature_thread.start()
gsr_thread.start()

# Join threads to keep the main program running
heart_rate_thread.join()
temperature_thread.join()
gsr_thread.join()
