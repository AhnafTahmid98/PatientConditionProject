import time
import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Set a threshold to detect the presence of a human body (in °C)
HUMAN_TEMP_THRESHOLD = 30.0  # Adjust this value as needed

try:
    while True:
        ambient_temp = mlx.ambient_temperature
        object_temp = mlx.object_temperature
        
        # Check if the object temperature indicates proximity to a human body
        if object_temp > HUMAN_TEMP_THRESHOLD:
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
