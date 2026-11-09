
#!/usr/bin/env python3

import socket
import subprocess
import time

import board
import adafruit_ssd1306
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont

from wifi_scanner import scan_networks
from nmap_scanner import discover_hosts, scan_tcp_ports
from network_tools import (
    ping_gateway,
    ping_internet,
    dns_lookup,
    get_network_info,
)


# ============================================================
# CONFIGURATION
# ============================================================

WIDTH = 128
HEIGHT = 64
REFRESH_SECONDS = 3

MENU = [
    "WiFi Dashboard",
    "Network Scanner",
    "Network Tools",
    "Nmap Scanner",
]

TOOLS = [
    "Gateway Ping",
    "Internet Ping",
    "DNS Lookup",
    "Network Info",
]

HOST_MENU = [
    "Scan TCP Ports",
    "Host Information",
]

PINS = {
    "UP": board.D17,
    "DOWN": board.D22,
    "LEFT": board.D27,
    "RIGHT": board.D23,
    "CENTER": board.D4,
    "A": board.D5,
    "B": board.D6,
}


# ============================================================
# OLED INITIALIZATION
# ============================================================

i2c = board.I2C()

oled = adafruit_ssd1306.SSD1306_I2C(
    WIDTH,
    HEIGHT,
    i2c,
    addr=0x3C
)

font = ImageFont.load_default()

buttons = {}

for name, pin in PINS.items():
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    buttons[name] = button


# ============================================================
# APPLICATION STATE
# ============================================================

screen = "menu"

selected = 0
tool_selected = 0

networks = []
network_selected = 0
scan_error = None

tool_result = []

hosts = []
host_selected = 0
host_subnet = ""
host_error = None

host_menu_selected = 0

port_scan_result = None
port_scan_error = None
port_selected = 0

last_refresh = 0


# ============================================================
# DISPLAY HELPERS
# ============================================================

def display(lines):
    """Draw up to six lines of text on the OLED."""

    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    for index, line in enumerate(lines[:6]):
        draw.text(
            (0, index * 10),
            str(line)[:21],
            font=font,
            fill=255
        )

    oled.image(image)
    oled.show()


def show_message(title, message):
    display([
        title,
        "--------------------",
        str(message)[:21],
    ])


def get_visible_items(items, current, count=4):
    """Return a scrollable portion of a list."""

    start = max(0, current - count + 1)

    if current < count:
        start = 0

    return start, items[start:start + count]


def format_result(value):
    """Convert tool output into OLED-friendly lines."""

    if value is None:
        return ["No result"]

    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            lines.append(f"{key}: {item}")
        return lines or ["No result"]

    if isinstance(value, (list, tuple)):
        lines = []
        for item in value:
            lines.extend(str(item).splitlines())
        return lines or ["No result"]

    if isinstance(value, bool):
        return ["Success" if value else "Failed"]

    return str(value).splitlines() or ["No result"]


# ============================================================
# MAIN MENU
# ============================================================

def show_menu():
    lines = [
        "PiScout v0.8",
        "--------------------"
    ]

    for index, item in enumerate(MENU):
        prefix = ">" if index == selected else " "
        lines.append(f"{prefix}{item}")

    display(lines)


# ============================================================
# WIFI DASHBOARD
# ============================================================

def get_wifi_info():
    ssid = "Not connected"
    ip = "Unknown"
    signal = "Unknown"

    try:
        result = subprocess.run(
            ["iwgetid", "-r"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.stdout.strip():
            ssid = result.stdout.strip()

    except Exception:
        pass

    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "dev", "wlan0"],
            capture_output=True,
            text=True,
            timeout=5
        )

        for part in result.stdout.split():
            if "/" in part and part.count(".") == 3:
                ip = part.split("/")[0]
                break

    except Exception:
        pass

    try:
        result = subprocess.run(
            ["iw", "dev", "wlan0", "link"],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.splitlines():
            if "signal:" in line:
                signal = line.split("signal:", 1)[1].strip()
                break

    except Exception:
        pass

    return ssid, ip, signal


def show_dashboard():
    ssid, ip, signal = get_wifi_info()

    display([
        "WiFi Dashboard",
        "--------------------",
        f"SSID: {ssid[:15]}",
        f"IP: {ip}",
        f"Signal: {signal[:13]}",
        "Left: Back"
    ])


# ============================================================
# WIFI NETWORK SCANNER
# ============================================================

def perform_wifi_scan():
    global networks, network_selected, scan_error

    show_message("WiFi Scanner", "Scanning...")

    try:
        result = scan_networks()
        networks = list(result or [])
        network_selected = 0
        scan_error = None

    except Exception as error:
        networks = []
        scan_error = str(error)
        print(f"WiFi scan error: {error}")


def wifi_field(network, key, default="Unknown"):
    if isinstance(network, dict):
        return network.get(key, default)
    return default


def show_network_list():
    if scan_error:
        display([
            "WiFi Scan Error",
            "--------------------",
            scan_error[:21],
            "B: Retry",
            "Left: Back"
        ])
        return

    if not networks:
        display([
            "WiFi Networks",
            "--------------------",
            "No networks found",
            "B: Rescan",
            "Left: Back"
        ])
        return

    start, visible = get_visible_items(
        networks, network_selected
    )

    lines = [
        f"WiFi Networks: {len(networks)}",
        "--------------------"
    ]

    for index, network in enumerate(visible, start):
        name = wifi_field(network, "ssid", "Hidden")
        name = str(name or "Hidden")

        prefix = ">" if index == network_selected else " "
        lines.append(f"{prefix}{name[:19]}")

    display(lines)


def show_network_details():
    if not networks:
        return

    network = networks[network_selected]

    ssid = wifi_field(network, "ssid", "Hidden")
    signal = wifi_field(network, "signal", "Unknown")
    channel = wifi_field(network, "channel", "Unknown")
    security = wifi_field(network, "security", "Unknown")

    display([
        "WiFi Details",
        "--------------------",
        f"SSID: {str(ssid)[:15]}",
        f"Signal: {signal}",
        f"Channel: {channel}",
        f"Sec: {str(security)[:16]}"
    ])


# ============================================================
# NETWORK TOOLS
# ============================================================

def show_tools_menu():
    lines = [
        "Network Tools",
        "--------------------"
    ]

    for index, item in enumerate(TOOLS):
        prefix = ">" if index == tool_selected else " "
        lines.append(f"{prefix}{item}")

    display(lines)


def execute_tool():
    global tool_result

    show_message("Network Tools", "Running...")

    try:
        if tool_selected == 0:
            result = ping_gateway()

        elif tool_selected == 1:
            result = ping_internet()

        elif tool_selected == 2:
            result = dns_lookup()

        elif tool_selected == 3:
            result = get_network_info()

        else:
            result = "Unknown tool"

        tool_result = format_result(result)

    except Exception as error:
        tool_result = [f"Error: {error}"]
        print(f"Network tool error: {error}")


def show_tool_result():
    display([
        TOOLS[tool_selected][:21],
        "--------------------",
        *tool_result[:3],
        "B: Retry"
    ])


# ============================================================
# NMAP HOST DISCOVERY
# ============================================================

def perform_host_discovery():
    global hosts, host_selected, host_subnet, host_error

    display([
        "Nmap Scanner",
        "--------------------",
        "Discovering hosts...",
        "Please wait"
    ])

    try:
        host_subnet, hosts = discover_hosts()
        hosts = list(hosts or [])
        host_selected = 0
        host_error = None

    except Exception as error:
        hosts = []
        host_error = str(error)
        print(f"Host discovery error: {error}")


def get_host_name(host):
    return str(
        host.get("name")
        or host.get("hostname")
        or host.get("ip")
        or "Unknown"
    )


def show_hosts():
    if host_error:
        display([
            "Nmap Error",
            "--------------------",
            host_error[:21],
            "",
            "B: Retry",
            "Left: Back"
        ])
        return

    if not hosts:
        display([
            "Nmap Scanner",
            "--------------------",
            "No hosts found",
            "",
            "B: Rescan",
            "Left: Back"
        ])
        return

    start, visible = get_visible_items(
        hosts, host_selected
    )

    lines = [
        f"Hosts: {len(hosts)}",
        "--------------------"
    ]

    for index, host in enumerate(visible, start):
        prefix = ">" if index == host_selected else " "
        name = get_host_name(host)

        lines.append(f"{prefix}{name[:19]}")

    display(lines)


# ============================================================
# HOST ACTION MENU
# ============================================================

def show_host_menu():
    if not hosts:
        return

    host = hosts[host_selected]

    lines = [
        get_host_name(host)[:21],
        host["ip"]
    ]

    for index, item in enumerate(HOST_MENU):
        prefix = ">" if index == host_menu_selected else " "
        lines.append(f"{prefix}{item}")

    lines.append("Left: Back")

    display(lines)


def show_host_details():
    if not hosts:
        return

    host = hosts[host_selected]

    display([
        "Host Information",
        "--------------------",
        f"Name: {get_host_name(host)[:15]}",
        f"IP: {host['ip']}",
        f"Status: {host.get('status', 'Unknown')}",
        f"MAC: {host.get('mac', 'Unknown')[:16]}"
    ])


# ============================================================
# TCP PORT SCANNING
# ============================================================

def perform_port_scan():
    global port_scan_result, port_scan_error, port_selected

    if not hosts:
        return

    host = hosts[host_selected]

    display([
        "TCP Port Scanner",
        "--------------------",
        host["ip"],
        "Scanning ports...",
        "Please wait"
    ])

    try:
        port_scan_result = scan_tcp_ports(host["ip"])
        port_scan_error = None
        port_selected = 0

        print(
            f"TCP scan complete: {host['ip']} - "
            f"{port_scan_result['open']} open, "
            f"{port_scan_result['closed']} closed, "
            f"{port_scan_result['filtered']} filtered"
        )

    except Exception as error:
        port_scan_result = None
        port_scan_error = str(error)
        print(f"TCP port scan error: {error}")


def get_open_ports():
    if not port_scan_result:
        return []

    return [
        port
        for port in port_scan_result["ports"]
        if port["state"] == "open"
    ]


def show_port_results():
    if port_scan_error:
        display([
            "Port Scan Error",
            "--------------------",
            port_scan_error[:21],
            "",
            "B: Retry",
            "Left: Back"
        ])
        return

    if not port_scan_result:
        display([
            "TCP Port Scanner",
            "--------------------",
            "No scan results",
            "",
            "B: Retry",
            "Left: Back"
        ])
        return

    open_ports = get_open_ports()

    if not open_ports:
        display([
            "TCP Scan Results",
            "--------------------",
            "No open TCP ports",
            f"Closed: {port_scan_result['closed']}",
            f"Filtered: {port_scan_result['filtered']}",
            "B: Retry"
        ])
        return

    start, visible = get_visible_items(
        open_ports, port_selected, count=3
    )

    lines = [
        f"Open: {port_scan_result['open']}",
        (
            f"C:{port_scan_result['closed']} "
            f"F:{port_scan_result['filtered']}"
        ),
        "--------------------"
    ]

    for index, port in enumerate(visible, start):
        prefix = ">" if index == port_selected else " "

        lines.append(
            f"{prefix}{port['port']} "
            f"{port['service'][:12]}"
        )

    display(lines)


# ============================================================
# SCREEN ROUTING
# ============================================================

def redraw():
    if screen == "menu":
        show_menu()

    elif screen == "dashboard":
        show_dashboard()

    elif screen == "scanner":
        show_network_list()

    elif screen == "details":
        show_network_details()

    elif screen == "tools":
        show_tools_menu()

    elif screen == "tool_result":
        show_tool_result()

    elif screen == "hosts":
        show_hosts()

    elif screen == "host_menu":
        show_host_menu()

    elif screen == "host_details":
        show_host_details()

    elif screen == "ports":
        show_port_results()


# ============================================================
# JOYSTICK / BUTTON NAVIGATION
# ============================================================

def handle_button(name):
    global screen
    global selected, tool_selected
    global network_selected, host_selected
    global host_menu_selected, port_selected
    global last_refresh

    # A always returns to the main menu.
    if name == "A":
        screen = "menu"
        redraw()
        return

    # MAIN MENU
    if screen == "menu":
        if name == "UP":
            selected = (selected - 1) % len(MENU)

        elif name == "DOWN":
            selected = (selected + 1) % len(MENU)

        elif name in ("CENTER", "RIGHT"):
            if selected == 0:
                screen = "dashboard"
                last_refresh = time.monotonic()

            elif selected == 1:
                screen = "scanner"
                perform_wifi_scan()

            elif selected == 2:
                screen = "tools"

            elif selected == 3:
                screen = "hosts"
                perform_host_discovery()

    # WIFI DASHBOARD
    elif screen == "dashboard":
        if name == "LEFT":
            screen = "menu"

    # WIFI SCANNER
    elif screen == "scanner":
        if name == "UP" and networks:
            network_selected = (
                network_selected - 1
            ) % len(networks)

        elif name == "DOWN" and networks:
            network_selected = (
                network_selected + 1
            ) % len(networks)

        elif name in ("CENTER", "RIGHT") and networks:
            screen = "details"

        elif name == "B":
            perform_wifi_scan()

        elif name == "LEFT":
            screen = "menu"

    # WIFI DETAILS
    elif screen == "details":
        if name == "LEFT":
            screen = "scanner"

        elif name == "B":
            screen = "scanner"
            perform_wifi_scan()

    # NETWORK TOOLS
    elif screen == "tools":
        if name == "UP":
            tool_selected = (
                tool_selected - 1
            ) % len(TOOLS)

        elif name == "DOWN":
            tool_selected = (
                tool_selected + 1
            ) % len(TOOLS)

        elif name in ("CENTER", "RIGHT"):
            screen = "tool_result"
            execute_tool()

        elif name == "LEFT":
            screen = "menu"

    # NETWORK TOOL RESULTS
    elif screen == "tool_result":
        if name == "LEFT":
            screen = "tools"

        elif name == "B":
            execute_tool()

    # DISCOVERED HOSTS
    elif screen == "hosts":
        if name == "UP" and hosts:
            host_selected = (
                host_selected - 1
            ) % len(hosts)

        elif name == "DOWN" and hosts:
            host_selected = (
                host_selected + 1
            ) % len(hosts)

        elif name in ("CENTER", "RIGHT") and hosts:
            host_menu_selected = 0
            screen = "host_menu"

        elif name == "B":
            perform_host_discovery()

        elif name == "LEFT":
            screen = "menu"

    # HOST ACTION MENU
    elif screen == "host_menu":
        if name == "UP":
            host_menu_selected = (
                host_menu_selected - 1
            ) % len(HOST_MENU)

        elif name == "DOWN":
            host_menu_selected = (
                host_menu_selected + 1
            ) % len(HOST_MENU)

        elif name in ("CENTER", "RIGHT"):
            if host_menu_selected == 0:
                screen = "ports"
                perform_port_scan()

            elif host_menu_selected == 1:
                screen = "host_details"

        elif name == "LEFT":
            screen = "hosts"

    # HOST INFORMATION
    elif screen == "host_details":
        if name == "LEFT":
            screen = "host_menu"

    # TCP PORT SCAN RESULTS
    elif screen == "ports":
        open_ports = get_open_ports()

        if name == "UP" and open_ports:
            port_selected = (
                port_selected - 1
            ) % len(open_ports)

        elif name == "DOWN" and open_ports:
            port_selected = (
                port_selected + 1
            ) % len(open_ports)

        elif name == "B":
            perform_port_scan()

        elif name == "LEFT":
            screen = "host_menu"

    redraw()


# ============================================================
# MAIN APPLICATION LOOP
# ============================================================

def main():
    global last_refresh

    print("Starting PiScout v0.8")

    previous_states = {
        name: False for name in buttons
    }

    redraw()
    last_refresh = time.monotonic()

    try:
        while True:
            for name, button in buttons.items():
                pressed = not button.value

                if pressed and not previous_states[name]:
                    handle_button(name)

                previous_states[name] = pressed

            # Automatically refresh the WiFi dashboard.
            if screen == "dashboard":
                now = time.monotonic()

                if now - last_refresh >= REFRESH_SECONDS:
                    show_dashboard()
                    last_refresh = now

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Stopping PiScout")

    finally:
        oled.fill(0)
        oled.show()

        for button in buttons.values():
            button.deinit()


if __name__ == "__main__":
    main()
