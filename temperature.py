import time
import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Updated human temperature range for stable detection
HUMAN_TEMP_RANGE = (34.0, 41.0)  # Adjusted human body temperature range
HUMAN_TEMP_THRESHOLD_OFFSET = 2.0  # Offset above ambient temperature for detection

# Function to get stable temperature readings by averaging
def get_stable_temperature(sensor, readings=10):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.05)  # Small delay between readings
    return temp_sum / readings

# Function to dynamically adjust the threshold based on ambient temp
def get_dynamic_threshold(ambient_temp, offset=HUMAN_TEMP_THRESHOLD_OFFSET):
    # Use ambient temp to set a dynamic threshold slightly above it
    return ambient_temp + offset

try:
    while True:
        ambient_temp = mlx.ambient_temperature
        object_temp = get_stable_temperature(mlx)
        
        # Dynamically set a human detection threshold close to ambient
        dynamic_threshold = get_dynamic_threshold(ambient_temp)

        # Check if the object temperature is within the human temperature range and above the dynamic threshold
        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1] and object_temp > dynamic_threshold:
            print("Human body detected.")
            print("Ambient Temperature: {:.2f}°C".format(ambient_temp))
            print("Human Body Temperature: {:.2f}°C".format(object_temp))
        else:
            # Measure object temperature (not human body)
            print("No human body detected.")
            print("Ambient Temperature: {:.2f}°C".format(ambient_temp))
            print("Object Temperature: {:.2f}°C".format(object_temp))

        # Pause briefly before the next reading
        time.sleep(1)

except KeyboardInterrupt:
    print("Temperature monitoring stopped.")
