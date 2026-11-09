
import ipaddress
import subprocess
import xml.etree.ElementTree as ET
import json 
from pathlib import Path

def get_local_subnet():
    result = subprocess.run(
        ["ip", "-4", "-o", "addr", "show", "dev", "wlan0"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True
    )

    fields = result.stdout.split()

    if "inet" not in fields:
        raise RuntimeError("No WiFi IPv4 address")

    cidr = fields[fields.index("inet") + 1]
    network = ipaddress.ip_interface(cidr).network

    if network.num_addresses > 256:
        raise RuntimeError("Subnet too large")

    return str(network)


ALIASES_FILE = Path(__file__).with_name("device_aliases.json")


def load_aliases():
    try:
        with open(ALIASES_FILE) as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def get_device_name(host, aliases):
    ip = host["ip"]

    if ip in aliases:
        return aliases[ip]

    if host.get("hostname"):
        return host["hostname"]

    if host.get("vendor") != "Unknown":
        return host["vendor"]

    return ip

def discover_hosts():
    subnet = get_local_subnet()

    result = subprocess.run(
        [
            "nmap",
            "-sn",
            "-R",
            "-oX", "-",
            subnet
        ],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Nmap failed"
        )

    root = ET.fromstring(result.stdout)
    hosts = []
    aliases = load_aliases()

    for host in root.findall("host"):
        status = host.find("status")

        if status is None or status.get("state") != "up":
            continue

        ip = None
        mac = "Unknown"
        vendor = "Unknown"
        hostname = None

        for address in host.findall("address"):
            if address.get("addrtype") == "ipv4":
                ip = address.get("addr")

            elif address.get("addrtype") == "mac":
                mac = address.get("addr", "Unknown")
                vendor = address.get("vendor", "Unknown")

        for name in host.findall("./hostnames/hostname"):
            value = name.get("name")
            if value:
                hostname = value
                break
        if ip:
            device = {
                "ip": ip,
                "mac": mac,
                "vendor": vendor,
                "hostname": hostname,
                "status": "Up"
            }

            device["name"] = get_device_name(device, aliases)

            hosts.append(device)

    hosts.sort(
        key=lambda host: ipaddress.ip_address(host["ip"])
    )

    return subnet, hosts



def scan_tcp_ports(ip):
    """Scan the 100 most common TCP ports on a host."""

    # Validate the target IPv4 address
    try:
        target = ipaddress.IPv4Address(ip)
    except ipaddress.AddressValueError:
        raise RuntimeError("Invalid IPv4 address")

    # Run Nmap TCP connect scan
    result = subprocess.run(
        [
            "nmap",
            "-sT",
            "-F",
            "-n",
            "-oX", "-",
            str(target)
        ],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Nmap scan failed"
        )

    # Parse Nmap XML output
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError:
        raise RuntimeError("Invalid Nmap XML output")

    ports = []

    # Extract individual port information
    for port in root.findall(".//port"):
        state = port.find("state")
        service = port.find("service")

        ports.append({
            "port": int(port.get("portid")),
            "protocol": port.get("protocol", "tcp"),
            "state": (
                state.get("state", "unknown")
                if state is not None else "unknown"
            ),
            "service": (
                service.get("name", "unknown")
                if service is not None else "unknown"
            )
        })

    # Count port states
    counts = {
        "open": 0,
        "closed": 0,
        "filtered": 0
    }

    for port in ports:
        state = port["state"]

        if state in counts:
            counts[state] += 1

    # Nmap groups unlisted ports in extraports
    for extra in root.findall(".//extraports"):
        state = extra.get("state", "")
        count = int(extra.get("count", "0"))

        if state in counts:
            counts[state] += count

    # Sort ports numerically
    ports.sort(key=lambda p: p["port"])

    return {
        "target": str(target),
        "ports": ports,
        "open": counts["open"],
        "closed": counts["closed"],
        "filtered": counts["filtered"]
    }

if __name__ == "__main__":
    subnet, hosts = discover_hosts()

    print(f"Subnet: {subnet}")
    print(f"Discovered: {len(hosts)} hosts")

    for host in hosts:
        print(host)
