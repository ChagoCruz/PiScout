
import re
import subprocess


def frequency_to_channel(freq):
    """Convert a 2.4 GHz frequency to its Wi-Fi channel."""
    if freq == 2484:
        return 14

    if 2412 <= freq <= 2472:
        return (freq - 2407) // 5

    return None


def get_security(block):
    """Identify advertised Wi-Fi security capabilities."""
    if re.search(r"Authentication suites:.*SAE", block):
        if re.search(r"Authentication suites:.*PSK", block):
            return "WPA2/WPA3"
        return "WPA3"

    if "RSN:" in block:
        return "WPA2"

    if "WPA:" in block:
        return "WPA"

    if re.search(r"capability:.*Privacy", block, re.I):
        return "Protected"

    return "Open"


def scan_networks():
    """Scan nearby Wi-Fi access points using iw."""
    try:
        result = subprocess.run(
            ["sudo", "-n", "iw", "dev", "wlan0", "scan"],
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip() or "Wi-Fi scan failed"
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError("Wi-Fi scan timed out")

    except FileNotFoundError:
        raise RuntimeError("iw is not installed")

    # Split output into individual access-point blocks.
    blocks = re.split(
        r"(?=^BSS [0-9a-fA-F:]{17})",
        result.stdout,
        flags=re.MULTILINE
    )

    networks = []

    for block in blocks:
        bssid_match = re.search(
            r"^BSS ([0-9a-fA-F:]{17})",
            block,
            re.MULTILINE
        )

        if not bssid_match:
            continue

        ssid_match = re.search(
            r"^\s*SSID:\s*(.*)$",
            block,
            re.MULTILINE
        )

        signal_match = re.search(
            r"^\s*signal:\s*(-?\d+(?:\.\d+)?)",
            block,
            re.MULTILINE
        )

        freq_match = re.search(
            r"^\s*freq:\s*(\d+(?:\.\d+)?)",
            block,
            re.MULTILINE
        )

        ssid = (
            ssid_match.group(1).strip()
            if ssid_match else ""
        )

        signal = (
            float(signal_match.group(1))
            if signal_match else -100.0
        )

        frequency = (
            int(float(freq_match.group(1)))
            if freq_match else 0
        )

        networks.append({
            "ssid": ssid or "<Hidden>",
            "bssid": bssid_match.group(1),
            "signal": signal,
            "frequency": frequency,
            "channel": frequency_to_channel(frequency),
            "security": get_security(block),
        })

    # Sort strongest signal first.
    networks.sort(
        key=lambda network: network["signal"],
        reverse=True
    )

    return networks


if __name__ == "__main__":
    for network in scan_networks():
        print(
            f"{network['ssid']:<20} "
            f"{network['signal']:>6.0f} dBm  "
            f"CH {str(network['channel']):<3} "
            f"{network['security']}"
        )
