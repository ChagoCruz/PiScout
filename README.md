# PiScout

**A Raspberry Pi-powered handheld network reconnaissance and diagnostic tool.**

PiScout is a portable network utility built with Python, a Raspberry Pi Zero 2 W, and an Adafruit OLED Bonnet. It provides a menu-driven interface for Wi-Fi scanning, network diagnostics, host discovery, and TCP port scanning using Nmap.

The goal of this project is to create a compact, standalone device for exploring and troubleshooting networks while developing practical skills in Linux, Python, networking, and cybersecurity.

**Current Version:** v0.8

## Features

### Wi-Fi Dashboard
- Display the currently connected Wi-Fi network (SSID).
- View the Raspberry Pi's local IPv4 address.
- Monitor Wi-Fi signal strength.
- Automatically refresh connection information.

### Wi-Fi Network Scanner
- Discover nearby Wi-Fi networks.
- Display network SSIDs.
- View signal strength, channel, and security information.
- Navigate discovered networks using the OLED joystick.

### Network Diagnostics
- **Gateway Ping:** Test connectivity to the local network gateway.
- **Internet Ping:** Test external connectivity.
- **DNS Lookup:** Verify DNS resolution.
- **Network Information:** Display local IP configuration, gateway, and DNS information.

### Nmap Host Discovery
- Automatically determine the local IPv4 subnet.
- Discover active hosts on the local network.
- Resolve available hostnames.
- Support custom device aliases.
- Browse discovered devices and view their network information.

### TCP Port Scanning
- Select a discovered host directly from the OLED interface.
- Scan the 100 most common TCP ports using Nmap.
- Identify open TCP ports and their commonly associated services.
- Display counts of open, closed, and filtered ports.
- Browse results and rescan devices using the joystick.

## Hardware

| Component | Description |
|---|---|
| Raspberry Pi Zero 2 W | Main computing platform |
| Adafruit 128×64 OLED Bonnet | SSD1306 I²C display with joystick and buttons |
| MicroSD Card | Operating system and application storage |
| Power Supply | Powers the Raspberry Pi |

PiScout currently runs on Raspberry Pi OS Lite and is controlled entirely through the OLED interface.

## Software Stack

- Python 3
- Raspberry Pi OS Lite
- Nmap
- Linux networking utilities (`ip`, `iw`, `ping`)
- Adafruit CircuitPython SSD1306
- Adafruit Blinka
- Pillow
- systemd

## Project Structure

```text
PiScout/
├── piscout.py          # Main application and OLED interface
├── nmap_scanner.py     # Host discovery and TCP scanning
├── wifi_scanner.py     # Nearby Wi-Fi network scanning
├── network_tools.py    # Ping, DNS, and network diagnostics
├── wifi_dashboard.py   # Wi-Fi dashboard utility
├── oled_test.py        # OLED hardware test
├── .gitignore
└── README.md
```

Local configuration files, virtual environments, and temporary files are excluded from version control.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ChagoCruz/PiScout.git
cd PiScout
```

### 2. Install system dependencies

On Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nmap iw wireless-tools
```

Enable I²C using:

```bash
sudo raspi-config
```

Navigate to **Interface Options → I2C → Enable**.

### 3. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install \
  adafruit-circuitpython-ssd1306 \
  adafruit-blinka \
  pillow
```

### 5. Run PiScout

```bash
python piscout.py
```

The application should initialize the OLED and display the PiScout main menu.

**Note:** Wi-Fi scanning requires appropriate permissions to execute `iw dev wlan0 scan`. The current development setup uses a restricted sudoers rule for this command. This permission must be configured separately on new installations.

## Controls

| Input | Action |
|---|---|
| Joystick Up | Move selection up |
| Joystick Down | Move selection down |
| Joystick Center | Select |
| Joystick Right | Select |
| Joystick Left | Go back |
| Button A | Return to main menu |
| Button B | Rescan or retry where supported |

## Nmap Scanning

PiScout integrates Nmap to perform network discovery and TCP port enumeration.

**Host discovery**

```bash
nmap -sn -R 192.168.1.0/24
```

This discovers responsive hosts and attempts hostname resolution. PiScout determines the subnet automatically rather than relying on a hardcoded address.

**TCP port scanning**

```bash
nmap -sT -F 192.168.1.100
```

This performs a TCP connect scan against the 100 most common TCP ports.

Port states include:

- **Open:** A service is accepting TCP connections.
- **Closed:** The port is reachable but no service is accepting connections.
- **Filtered:** Network filtering prevents Nmap from determining the port's state.

The scanner parses Nmap's XML output and presents the results on the OLED.

Service labels from basic scans represent commonly associated services and do not necessarily identify the actual running software.

## Automatic Startup

PiScout can run automatically at boot using a systemd service.

The development installation uses:

```text
/etc/systemd/system/piscout.service
```

After configuring the service for the correct installation path and user, it can be managed with:

```bash
sudo systemctl start piscout
sudo systemctl stop piscout
sudo systemctl restart piscout
sudo systemctl status piscout
```

## Roadmap

- [x] OLED menu and joystick navigation
- [x] Wi-Fi dashboard
- [x] Nearby Wi-Fi discovery
- [x] Network connectivity diagnostics
- [x] Nmap host discovery
- [x] Hostname resolution and device aliases
- [x] TCP port scanning
- [x] Open, closed, and filtered port summaries
- [ ] Standard and custom port scan profiles
- [ ] Service and version detection (`nmap -sV`)
- [ ] Improved device identification
- [ ] Scan history and saved results
- [ ] Battery-powered portable enclosure

## Security and Responsible Use

PiScout is intended for network administration, troubleshooting, cybersecurity education, and authorized security assessments.

Only scan networks and devices that you own or have explicit permission to assess.

## Project Status

**Active Development — v0.8**

PiScout is a personal hardware and software project focused on learning through hands-on network analysis and tool development.

Future versions will expand its reconnaissance capabilities and improve the handheld interface.

## Author

Developed by [ChagoCruz](https://github.com/ChagoCruz).

**Repository:** https://github.com/ChagoCruz/PiScout
