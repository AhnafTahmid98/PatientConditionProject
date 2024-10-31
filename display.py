import time
import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# Initialize I2C and OLED display
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Clear the display
oled.fill(0)
oled.show()

# Create a blank image for drawing
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)

# Load default font or a larger one if available
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except IOError:
    font = ImageFont.load_default()

# Draw "Display Test" text
draw.text((0, 0), "Display Test", font=font, fill=255)

# Display image on OLED
oled.image(image)
oled.show()

# Wait for a few seconds to view the message
time.sleep(5)

# Clear the display after test
oled.fill(0)
oled.show()
