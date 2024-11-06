import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import threading

# Initialize I2C bus and ADC
def initialize_devices():
    i2c = busio.I2C(board.SCL, board.SDA)
    time.sleep(0.5)  # Short delay for stability
    adc = ADS1115(i2c)
    adc.gain = 1
    return adc

# Set up initial I2C devices
adc = initialize_devices()

# Moving average filter settings for GSR
window_size = 10
gsr_readings = []

# Baseline and thresholds for GSR (adjust based on observations)
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

# GSR Functionality
def read_gsr():
    chan_gsr = AnalogIn(adc, 1)
    return chan_gsr.value

def get_moving_average_gsr(value):
    gsr_readings.append(value)
    if len(gsr_readings) > window_size:
        gsr_readings.pop(0)
    return sum(gsr_readings) / len(gsr_readings)

def determine_stress_level(smoothed_value):
    if smoothed_value < relaxed_threshold:
        return "Relaxed"
    elif relaxed_threshold <= smoothed_value < normal_threshold:
        return "Normal"
    elif normal_threshold <= smoothed_value < elevated_threshold:
        return "Elevated"
    else:
        return "High"

# Heart Rate Functionality
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

def monitor_heart_rate():
    global last_pulse_time, first_pulse
    chan_heart_rate = AnalogIn(adc, 0)

    print("Starting heart rate measurement on A0...")
    while True:
        voltage = chan_heart_rate.voltage
        print(f"Voltage on A0: {voltage:.3f} V")

        if voltage > high_threshold and first_pulse:
            print("Pulse detected (first pulse)")
            last_pulse_time = time.time()
            first_pulse = False

        elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
            pulse_interval = (time.time() - last_pulse_time) * 1000  # ms
            last_pulse_time = time.time()
            bpm = 60000 / pulse_interval
            print(f"Heart Rate: {bpm:.2f} BPM")

        time.sleep(0.1)

# GSR Monitoring Thread
def monitor_gsr():
    while True:
        try:
            gsr_value = read_gsr()
            smoothed_value = get_moving_average_gsr(gsr_value)
            
            if smoothed_value < 13000:
                contact_status = "Contact with human detected"
                stress_level = determine_stress_level(smoothed_value)
                print(f"{contact_status} | Stress Level: {stress_level} | Smoothed GSR Value: {smoothed_value}")
            else:
                print("No contact detected")

            time.sleep(3)  # Increase delay to reduce I2C load

        except OSError as e:
            print("I2C communication error. Reinitializing I2C bus...")
            adc = initialize_devices()  # Reinitialize the I2C device

# Main function to start both threads
if __name__ == "__main__":
    try:
        # Create threads for GSR and Heart Rate monitoring
        gsr_thread = threading.Thread(target=monitor_gsr)
        heart_rate_thread = threading.Thread(target=monitor_heart_rate)

        # Start the threads
        gsr_thread.start()
        heart_rate_thread.start()

        # Keep the main thread alive
        gsr_thread.join()
        heart_rate_thread.join()

    except KeyboardInterrupt:
        print("Program stopped.")
