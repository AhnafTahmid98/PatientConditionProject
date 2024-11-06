import time
import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Updated human temperature range and offset for improved detection
HUMAN_TEMP_RANGE = (30.0, 42.0)  # Slightly expanded range for human body temperature
HUMAN_TEMP_THRESHOLD_OFFSET = 3.0  # Increased offset above ambient temperature

# Function to get stable temperature readings by averaging
def get_stable_temperature(sensor, readings=15):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.05)  # Small delay between readings
    return temp_sum / readings

# Function to dynamically adjust the threshold based on ambient temperature
def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    return ambient_temp + offset

try:
    while True:
        # Measure and display ambient (environmental) temperature
        ambient_temp = mlx.ambient_temperature
        print("Environmental Temperature: {:.2f}°C".format(ambient_temp))

        # Get a stable reading for object temperature to check for human presence
        object_temp = get_stable_temperature(mlx)

        # Set a dynamic threshold based on the ambient temperature
        dynamic_threshold = get_dynamic_threshold(ambient_temp)

        # Check if object temperature meets human detection criteria
        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
            print("Human body detected.")
            print("Human Body Temperature: {:.2f}°C".format(object_temp))
        else:
            print("No human body detected.")

        # Pause briefly before the next reading
        time.sleep(1)

except KeyboardInterrupt:
    print("Temperature monitoring stopped.")
