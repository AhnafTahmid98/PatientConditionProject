import board
import busio
import adafruit_mlx90614

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create MLX90614 object
mlx = adafruit_mlx90614.MLX90614(i2c)

# Read and print temperature data
print("Ambient Temperature: {:.2f}°C".format(mlx.ambient_temperature))
print("Object Temperature: {:.2f}°C".format(mlx.object_temperature))

# You can use this part to send data to your mobile app or server
