
import time
import board
import busio
import adafruit_ssd1306

# Create I2C interface
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize the display (width: 128, height: 64)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Clear the display
oled.fill(0)
oled.show()

# Display a test message
oled.text("Hello, Ahnaf!", 0, 0, 1)
oled.show()

# Wait for 5 seconds to view the message
time.sleep(5)

# Clear the display again
oled.fill(0)
oled.show()
