import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_mlx90614
import adafruit_ssd1306
import threading
from PIL import Image, ImageDraw, ImageFont

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize ADC, Temperature Sensor, and OLED
adc = ADS1115(i2c, address=0x48)
adc.gain = 1
mlx = adafruit_mlx90614.MLX90614(i2c, address=0x5a)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

# Shared variables for display
bpm_value = 0
temperature_value = 0
stress_level = "None"
bpm_history = []  # To store recent BPM values for graph

# Lock for synchronizing display updates
data_lock = threading.Lock()
running = True  # Flag to control the loop

# Settings for GSR
window_size = 10
gsr_readings = []
baseline_value = 11000
relaxed_threshold = baseline_value * 0.9
normal_threshold = baseline_value * 1.1
elevated_threshold = baseline_value * 1.3

# GSR Functions
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
        return "Normal"
    elif relaxed_threshold <= smoothed_value < normal_threshold:
        return "Normal"
    elif normal_threshold <= smoothed_value < elevated_threshold:
        return "Elevated"
    else:
        return "High"

# Heart Rate Functions
high_threshold = 2.5
low_threshold = 1.5
last_pulse_time = 0
first_pulse = True

def monitor_heart_rate():
    global adc, bpm_value, last_pulse_time, first_pulse, bpm_history
    while running:
        try:
            chan_heart_rate = AnalogIn(adc, 0)
            voltage = chan_heart_rate.voltage
            if voltage > high_threshold and first_pulse:
                last_pulse_time = time.time()
                first_pulse = False

            elif voltage > high_threshold and time.time() - last_pulse_time > 0.4:
                pulse_interval = (time.time() - last_pulse_time) * 1000  # ms
                last_pulse_time = time.time()
                bpm_value = 60000 / pulse_interval

                # Add bpm_value to bpm_history for graphing, keeping the list length fixed
                with data_lock:
                    bpm_history.append(bpm_value)
                    if len(bpm_history) > 20:  # Maintain a max history length of 20 for graph
                        bpm_history.pop(0)
                    
                    print(f"Heart Rate: {bpm_value:.2f} BPM")
            time.sleep(0.1)

        except OSError:
            print("I2C communication error in heart rate monitoring. Reinitializing ADS1115...")
            adc = ADS1115(i2c, address=0x48)
            time.sleep(1)

# GSR Monitoring Thread
def monitor_gsr():
    global adc, stress_level
    while running:
        try:
            gsr_value = read_gsr()
            smoothed_value = get_moving_average_gsr(gsr_value)
            if smoothed_value < 13000:
                contact_status = "Contact with human detected"
                stress_level = determine_stress_level(smoothed_value)
                with data_lock:
                    print(f"{contact_status} | Stress Level: {stress_level} | Smoothed GSR Value: {smoothed_value}")
            else:
                with data_lock:
                    stress_level = "No contact"
            time.sleep(3)

        except OSError:
            print("I2C communication error in GSR monitoring. Reinitializing ADS1115...")
            adc = ADS1115(i2c, address=0x48)
            time.sleep(1)

# Temperature Monitoring Functions
HUMAN_TEMP_RANGE = (35.8, 38.0)
HUMAN_TEMP_THRESHOLD_OFFSET = 2.5
MAX_ATTEMPTS = 3

def get_stable_temperature(sensor, readings=20):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.02)
    return temp_sum / readings

def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

def monitor_temperature():
    global temperature_value, HUMAN_TEMP_THRESHOLD_OFFSET
    no_detection_count = 0
    while running:
        object_temp = get_stable_temperature(mlx)
        dynamic_threshold = get_dynamic_threshold(mlx.ambient_temperature)

        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
            temperature_value = object_temp
            with data_lock:
                print(f"Human Body Temperature: {temperature_value:.2f}°C")
            no_detection_count = 0
        else:
            no_detection_count += 1
            with data_lock:
                temperature_value = 0
                print("No human body detected.")

        if no_detection_count >= MAX_ATTEMPTS:
            HUMAN_TEMP_THRESHOLD_OFFSET += 0.1
            no_detection_count = 0
        time.sleep(1)

# OLED Display Thread with Simple Font and Graph
def update_display():
    # Use DejaVu Sans with font size 10 for better readability and spacing
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except IOError:
        font = ImageFont.load_default()
    
    while running:
        with data_lock:
            # Create a blank image for drawing with smaller font
            image = Image.new("1", (128, 64))
            draw = ImageDraw.Draw(image)
            
            # Display BPM with actual value, Temperature, and Stress Level with adjusted spacing
            draw.text((0, 0), f"BPM: {bpm_value:.2f}", font=font, fill=255)
            
            # Draw BPM Graph with thicker lines for better clarity
            if bpm_history:
                max_bpm = max(bpm_history) if max(bpm_history) > 0 else 1
                min_bpm = min(bpm_history)
                graph_height = 10
                graph_width = 60
                x_start = 0
                y_start = 12

                # Draw graph as thicker lines for clarity
                for i in range(1, len(bpm_history)):
                    # Scale y-values to fit within the graph height
                    y1 = y_start + graph_height - int((bpm_history[i-1] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    y2 = y_start + graph_height - int((bpm_history[i] - min_bpm) / (max_bpm - min_bpm) * graph_height)
                    x1 = x_start + (i - 1) * (graph_width // (len(bpm_history) - 1))
                    x2 = x_start + i * (graph_width // (len(bpm_history) - 1))
                    draw.line((x1, y1, x2, y2), fill=255, width=2)

            # Display Temperature and Stress Level
            draw.text((0, 24), f"Temp.: {temperature_value:.2f}C", font=font, fill=255)
            draw.text((0, 44), f"Stress: {stress_level}", font=font, fill=255)

            # Update OLED display
            oled.image(image)
            oled.show()
        
        # Refresh less frequently to avoid blur
        time.sleep(1.5)

# Main function to start all threads
if __name__ == "__main__":
    try:
        gsr_thread = threading.Thread(target=monitor_gsr)
        heart_rate_thread = threading.Thread(target=monitor_heart_rate)
        temperature_thread = threading.Thread(target=monitor_temperature)
        display_thread = threading.Thread(target=update_display)

        gsr_thread.start()
        heart_rate_thread.start()
        temperature_thread.start()
        display_thread.start()

        gsr_thread.join()
        heart_rate_thread.join()
        temperature_thread.join()
        display_thread.join()

    except KeyboardInterrupt:
        print("Monitoring stopped.")
        running = False  # Set the flag to stop all threads
