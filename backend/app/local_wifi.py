"""
Reads real Wi-Fi stats for the one device we actually have: the laptop
running this backend. No router login, no monitor mode, no extra
hardware, just the OS reporting on the adapter it already owns.

This only fills in for the built-in OS commands on whatever platform
we're running on, and quietly returns None if none of them work (for
example when running inside a container with no wireless adapter,
which is exactly the environment this gets tested in most of the
time). When it does work, its output gets folded into the dashboard as
one real, live device sitting alongside the simulated ones.
"""

from __future__ import annotations

import platform
import re
import subprocess

from app.models import Band


def _run(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def read_local_adapter_state() -> dict | None:
    system = platform.system()

    if system == "Linux":
        return _read_linux()
    if system == "Windows":
        return _read_windows()
    if system == "Darwin":
        return _read_macos()
    return None

def read_local_mac_address() -> str | None:
    system = platform.system()

    if system == "Windows":
        output = _run(["getmac", "/fo", "csv", "/v"])
        if not output:
            return None

        for line in output.splitlines():
            if "Wi-Fi" not in line and "Wireless" not in line:
                continue

            mac_match = re.search(
                r"([0-9A-Fa-f]{2}(?:[-:][0-9A-Fa-f]{2}){5})",
                line,
            )

            if mac_match:
                return mac_match.group(1)

    elif system == "Linux":
        output = _run(["ip", "link"])
        if not output:
            return None

        mac_match = re.search(
            r"link/ether\s+([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})",
            output,
        )

        if mac_match:
            return mac_match.group(1)

    elif system == "Darwin":
        output = _run(["ifconfig"])
        if not output:
            return None

        mac_match = re.search(
            r"ether\s+([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})",
            output,
        )

        if mac_match:
            return mac_match.group(1)

    return None

def _read_linux() -> dict | None:
    output = _run(["nmcli", "-t", "-f", "active,signal,chan,rate,freq", "dev", "wifi"])
    if not output:
        return None
    for line in output.splitlines():
        fields = line.split(":")
        if len(fields) < 5 or fields[0] != "yes":
            continue
        signal_pct, channel, rate_str, freq_str = fields[1], fields[2], fields[3], fields[4]
        rssi = _percent_to_dbm(int(signal_pct)) if signal_pct.isdigit() else -65.0
        freq_mhz = int(re.sub(r"\D", "", freq_str) or 0)
        return {
            "rssi_dbm": rssi,
            "channel": int(channel) if channel.isdigit() else 0,
            "link_rate_mbps": float(re.sub(r"[^\d.]", "", rate_str) or 0),
            "band": _band_from_freq(freq_mhz),
        }
    return None


def _read_windows() -> dict | None:
    output = _run(["netsh", "wlan", "show", "interfaces"])
    if not output:
        return None
    signal_match = re.search(r"Signal\s*:\s*(\d+)%", output)
    rate_match = re.search(r"Receive rate \(Mbps\)\s*:\s*([\d.]+)", output)
    channel_match = re.search(r"Channel\s*:\s*(\d+)", output)
    if not signal_match:
        return None
    rssi = _percent_to_dbm(int(signal_match.group(1)))
    channel = int(channel_match.group(1)) if channel_match else 0
    return {
        "rssi_dbm": rssi,
        "channel": channel,
        "link_rate_mbps": float(rate_match.group(1)) if rate_match else 0.0,
        "band": Band.GHZ_5 if channel > 14 else Band.GHZ_2_4,
    }


def _read_macos() -> dict | None:
    output = _run(["wdutil", "info"])
    if not output:
        return None
    rssi_match = re.search(r"RSSI\s*:\s*(-?\d+)", output)
    channel_match = re.search(r"Channel\s*:\s*(\d+)", output)
    rate_match = re.search(r"Tx Rate\s*:\s*([\d.]+)", output)
    if not rssi_match:
        return None
    channel = int(channel_match.group(1)) if channel_match else 0
    return {
        "rssi_dbm": float(rssi_match.group(1)),
        "channel": channel,
        "link_rate_mbps": float(rate_match.group(1)) if rate_match else 0.0,
        "band": Band.GHZ_5 if channel > 14 else Band.GHZ_2_4,
    }


def _percent_to_dbm(percent: int) -> float:
    # rough linear mapping, OS signal percentages are already a lossy
    # summary of the real RSSI so this is deliberately approximate
    return -100 + (percent * 0.5)


def _band_from_freq(freq_mhz: int) -> Band:
    if freq_mhz >= 5925:
        return Band.GHZ_6
    if freq_mhz >= 5150:
        return Band.GHZ_5
    return Band.GHZ_2_4
