import time
import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Human temperature range and offset
HUMAN_TEMP_RANGE = (35.8, 38.0)
HUMAN_TEMP_THRESHOLD_OFFSET = 2.5  # Starting offset for human detection
MAX_ATTEMPTS = 5  # Number of failed attempts before increasing offset

# Function to get stable temperature readings with a weighted moving average
def get_stable_temperature(sensor, readings=20):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.02)  # Shorter delay between samples for faster averaging
    return temp_sum / readings

# Function to dynamically adjust the threshold based on ambient temperature
def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

try:
    no_detection_count = 0  # Count of failed human detections

    while True:
        # Get a stable reading for object temperature
        object_temp = get_stable_temperature(mlx)

        # Set a dynamic threshold based on ambient temperature
        dynamic_threshold = get_dynamic_threshold(mlx.ambient_temperature)

        # Check if object temperature meets human detection criteria
        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
            print("Human body detected.")
            print("Human Body Temperature: {:.2f}°C".format(object_temp))
            no_detection_count = 0  # Reset count on successful detection
        else:
            no_detection_count += 1
            print("No human body detected.")

        # Adaptively increase threshold if repeated failures occur
        if no_detection_count >= MAX_ATTEMPTS:
            HUMAN_TEMP_THRESHOLD_OFFSET += 0.1  # Slightly increase offset
            print(f"Increasing detection offset to {HUMAN_TEMP_THRESHOLD_OFFSET:.1f}°C")
            no_detection_count = 0  # Reset count after adjustment

        # Pause briefly before the next reading
        time.sleep(1)

except KeyboardInterrupt:
    print("Temperature monitoring stopped.")
