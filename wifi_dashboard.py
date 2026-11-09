
import time
import socket
import subprocess

import board
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# OLED configuration
WIDTH = 128
HEIGHT = 64
REFRESH_SECONDS = 3

i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(
    WIDTH, HEIGHT, i2c, addr=0x3C
)

font = ImageFont.load_default()


def run_command(command):
    """Run a Linux command and return its output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def get_wifi_info():
    """Get current Wi-Fi SSID and signal strength."""
    output = run_command(["iw", "dev", "wlan0", "link"])

    ssid = "Disconnected"
    signal = "--"

    for line in output.splitlines():
        line = line.strip()

        if line.startswith("SSID:"):
            ssid = line.split(":", 1)[1].strip()

        elif line.startswith("signal:"):
            signal = line.split(":", 1)[1].strip()

    return ssid, signal


def get_ip_address():
    """Get wlan0's IPv4 address."""
    output = run_command([
        "ip", "-4", "-o", "addr", "show", "dev", "wlan0"
    ])

    for field_index, field in enumerate(output.split()):
        if field == "inet":
            return output.split()[field_index + 1].split("/")[0]

    return "No IP"


def draw_dashboard():
    ssid, signal = get_wifi_info()
    ip_address = get_ip_address()

    connected = ssid != "Disconnected"
    status = "Connected" if connected else "Offline"

    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    # Header
    draw.text((0, 0), "PiScout v0.2", font=font, fill=255)
    draw.line((0, 11, 127, 11), fill=255)

    # Wi-Fi information
    draw.text((0, 14), f"SSID: {ssid[:15]}", font=font, fill=255)
    draw.text((0, 24), f"IP: {ip_address}", font=font, fill=255)
    draw.text((0, 34), f"Signal: {signal}", font=font, fill=255)
    draw.text((0, 44), f"Link: {status}", font=font, fill=255)

    # Footer
    draw.line((0, 54, 127, 54), fill=255)
    draw.text((0, 56), "Refresh: 3s", font=font, fill=255)

    oled.image(image)
    oled.show()


try:
    oled.fill(0)
    oled.show()

    while True:
        draw_dashboard()
        time.sleep(REFRESH_SECONDS)

except KeyboardInterrupt:
    oled.fill(0)
    oled.show()
    print("\nPiScout dashboard stopped.")
