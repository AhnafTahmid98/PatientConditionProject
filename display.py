from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Clear the display
oled.fill(0)
oled.show()

# Create a blank image for drawing
image = Image.new('1', (128, 64))
draw = ImageDraw.Draw(image)

# Load a font (path to a .ttf file or use default)
font = ImageFont.load_default()

# Draw text
draw.text((0, 0), "Hello, Ahnaf!", font=font, fill=255)

# Display image
oled.image(image)
oled.show()
