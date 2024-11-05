import time
import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Set a threshold to detect the presence of a human body
HUMAN_TEMP_THRESHOLD = 30.0  # Adjust based on initial testing
HUMAN_TEMP_RANGE = (30.0, 40.0)  # Typical human body temperature range in °C

# Function to get stable temperature readings by averaging
def get_stable_temperature(sensor, readings=5):
    temp_sum = 0
    for _ in range(readings):
        temp_sum += sensor.object_temperature
        time.sleep(0.1)  # Small delay between readings
    return temp_sum / readings

try:
    while True:
        ambient_temp = mlx.ambient_temperature
        object_temp = get_stable_temperature(mlx)
        
        # Check if the object temperature is within the human body temperature range
        if HUMAN_TEMP_RANGE[0] <= object_temp <= HUMAN_TEMP_RANGE[1]:
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
