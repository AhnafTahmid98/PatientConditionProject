import time
import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Fine-tuned human temperature range and offset settings
HUMAN_TEMP_RANGE = (35.0, 39.0)
HUMAN_TEMP_THRESHOLD_OFFSET = 0.5  # Lowered offset
MAX_ATTEMPTS = 5  # Number of failed attempts before increasing offset

# Function to get stable temperature readings with a weighted moving average
def get_weighted_average(sensor, readings=20):
    total_weighted_temp = 0
    total_weight = 0
    for i in range(readings):
        weight = readings - i  # More recent readings get higher weight
        temp = sensor.object_temperature
        total_weighted_temp += temp * weight
        total_weight += weight
        time.sleep(0.02)  # Shorter delay between samples
    return total_weighted_temp / total_weight

# Function to dynamically adjust the threshold based on ambient temperature
def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

try:
    no_detection_count = 0  # Count of failed human detections

    while True:
        # Measure and display ambient (environmental) temperature
        ambient_temp = mlx.ambient_temperature
        print("Environmental Temperature: {:.2f}°C".format(ambient_temp))

        # Get a stable reading for object temperature
        object_temp = get_weighted_average(mlx)

        # Set a dynamic threshold based on the ambient temperature
        dynamic_threshold = get_dynamic_threshold(ambient_temp)

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
