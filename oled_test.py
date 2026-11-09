import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# Initialize I2C
i2c = board.I2C()

# Initialize 128x64 OLED at address 0x3C
oled = adafruit_ssd1306.SSD1306_I2C(
    128, 64, i2c, addr=0x3C
)

# Clear the display
oled.fill(0)
oled.show()

# Create a monochrome image
image = Image.new("1", (128, 64))
draw = ImageDraw.Draw(image)

# Draw text
draw.text((0, 0), "PiScout v0.1", fill=255)
draw.text((0, 18), "OLED: Connected", fill=255)
draw.text((0, 36), "I2C: 0x3C", fill=255)
draw.text((0, 54), "Status: Ready", fill=255)

# Display the image
oled.image(image)
oled.show()
