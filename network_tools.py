
import ipaddress
import re
import socket
import subprocess


def run_command(args, timeout=10):
    """Run a Linux command and return its output."""
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(str(error))


def get_gateway():
    """Discover the default IPv4 gateway."""
    result = run_command(
        ["ip", "-4", "route", "show", "default"]
    )

    for line in result.stdout.splitlines():
        fields = line.split()

        if "via" in fields:
            return fields[fields.index("via") + 1]

    return None


def get_network_info():
    """Get the Pi's IPv4 network configuration."""
    result = run_command([
        "ip", "-4", "-o", "addr", "show", "dev", "wlan0"
    ])

    ip_address = "Unavailable"
    subnet = "Unavailable"

    fields = result.stdout.split()

    if "inet" in fields:
        cidr = fields[fields.index("inet") + 1]
        interface = ipaddress.ip_interface(cidr)
        ip_address = str(interface.ip)
        subnet = str(interface.network.netmask)

    gateway = get_gateway() or "Unavailable"

    dns_servers = []

    try:
        with open("/etc/resolv.conf") as file:
            for line in file:
                if line.startswith("nameserver"):
                    dns_servers.append(line.split()[1])
    except OSError:
        pass

    return {
        "ip": ip_address,
        "subnet": subnet,
        "gateway": gateway,
        "dns": dns_servers[0] if dns_servers else "Unavailable"
    }


def ping_host(host, count=3):
    """Ping a host and return packet-loss and latency results."""
    result = run_command(
        ["ping", "-n", "-c", str(count), "-W", "2", host],
        timeout=count * 3 + 3
    )

    output = result.stdout

    packet_match = re.search(
        r"(\d+) packets transmitted,\s*(\d+) received",
        output
    )

    latency_match = re.search(
        r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev)"
        r"\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)",
        output
    )

    if not packet_match:
        raise RuntimeError(
            result.stderr.strip() or "Ping failed"
        )

    sent = int(packet_match.group(1))
    received = int(packet_match.group(2))

    loss = (
        (sent - received) / sent * 100
        if sent else 100
    )

    average = (
        float(latency_match.group(2))
        if latency_match else None
    )

    return {
        "host": host,
        "sent": sent,
        "received": received,
        "loss": loss,
        "avg": average
    }


def ping_gateway():
    """Ping the current default gateway."""
    gateway = get_gateway()

    if not gateway:
        raise RuntimeError("No default gateway")

    return ping_host(gateway)


def ping_internet():
    """Test external IPv4 connectivity."""
    return ping_host("1.1.1.1")


def dns_lookup(host="example.com"):
    """Resolve a hostname using the configured DNS resolver."""
    try:
        results = socket.getaddrinfo(
            host,
            None,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM
        )

        addresses = sorted({
            item[4][0] for item in results
        })

        return {
            "host": host,
            "address": addresses[0]
        }

    except socket.gaierror as error:
        raise RuntimeError(f"DNS failed: {error}")
