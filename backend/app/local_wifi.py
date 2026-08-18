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
import time
import uuid

from app.models import Band, WifiStandard


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


def _active_wifi_iface() -> str | None:
    output = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
    if not output:
        return None
    for line in output.splitlines():
        fields = line.split(":")
        if len(fields) >= 3 and fields[1] == "wifi" and fields[2] == "connected":
            return fields[0]
    return None


def _read_linux() -> dict | None:
    """
    Deliberately does NOT use `nmcli dev wifi` for the live reading:
    that command returns NetworkManager's periodic scan cache, which
    can go tens of seconds between refreshes and produces a flat line
    when polled every couple of seconds. `iw dev <iface> link` instead
    asks the driver for the live state of the current association, so
    every poll reflects the real current signal.
    """
    iface = _active_wifi_iface()
    if not iface:
        return None

    link_output = _run(["iw", "dev", iface, "link"])
    if not link_output:
        return None

    rssi_match = re.search(r"signal:\s*(-?\d+)\s*dBm", link_output)
    if not rssi_match:
        return None

    rate_match = re.search(r"tx bitrate:\s*([\d.]+)", link_output)
    freq_match = re.search(r"freq:\s*(\d+)", link_output)
    freq_mhz = int(freq_match.group(1)) if freq_match else 0

    retry_rate_pct, packet_loss_pct = _read_linux_retry_stats(iface)

    return {
        "rssi_dbm": float(rssi_match.group(1)),
        "channel": _channel_from_freq(freq_mhz),
        "link_rate_mbps": float(rate_match.group(1)) if rate_match else 0.0,
        "band": _band_from_freq(freq_mhz),
        "retry_rate_pct": retry_rate_pct,
        "packet_loss_pct": packet_loss_pct,
    }


# Running totals from the last poll, so retry/loss rates can be
# computed as a delta rather than faked. Module-level because there's
# only ever one real adapter being tracked in this process.
_LAST_STATION_COUNTERS: dict | None = None


def _read_linux_retry_stats(iface: str) -> tuple[float, float]:
    """
    Retry rate and packet loss for the real device, computed from live
    driver counters instead of a hardcoded constant. `iw station dump`
    reports running totals since association, not a rate, so a single
    snapshot can't tell you anything -- this keeps the previous
    snapshot around and diffs against it each poll. The very first
    poll after the backend starts has nothing to diff against yet, so
    it reports 0 until the second poll, ~2 seconds later.
    """
    global _LAST_STATION_COUNTERS

    output = _run(["iw", "dev", iface, "station", "dump"])
    if not output:
        return 0.0, 0.0

    tx_packets = _extract_int(output, r"tx packets:\s*(\d+)")
    if tx_packets is None:
        return 0.0, 0.0

    current = {
        "tx_packets": tx_packets,
        "tx_retries": _extract_int(output, r"tx retries:\s*(\d+)") or 0,
        "tx_failed": _extract_int(output, r"tx failed:\s*(\d+)") or 0,
        "rx_drop": _extract_int(output, r"rx drop misc:\s*(\d+)") or 0,
        "timestamp": time.time(),
    }

    previous = _LAST_STATION_COUNTERS
    _LAST_STATION_COUNTERS = current

    if previous is None:
        return 0.0, 0.0

    delta_packets = current["tx_packets"] - previous["tx_packets"]
    if delta_packets <= 0:
        # counters reset (roaming/reassociation) or nothing sent this
        # interval -- can't compute a meaningful rate either way
        return 0.0, 0.0

    delta_retries = max(0, current["tx_retries"] - previous["tx_retries"])
    delta_failed = max(0, current["tx_failed"] - previous["tx_failed"])
    delta_drop = max(0, current["rx_drop"] - previous["rx_drop"])

    retry_rate_pct = min(100.0, (delta_retries / delta_packets) * 100)
    packet_loss_pct = min(100.0, ((delta_failed + delta_drop) / delta_packets) * 100)

    return retry_rate_pct, packet_loss_pct


def _extract_int(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


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
        # netsh doesn't expose retry/failure counters the way `iw` does
        # on Linux, so these stay at 0 on Windows for now.
        "retry_rate_pct": 0.0,
        "packet_loss_pct": 0.0,
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
        # wdutil doesn't surface retry/failure counters either, same
        # limitation as Windows.
        "retry_rate_pct": 0.0,
        "packet_loss_pct": 0.0,
    }


def _percent_to_dbm(percent: int) -> float:
    return -100 + (percent * 0.5)


def _band_from_freq(freq_mhz: int) -> Band:
    if freq_mhz >= 5925:
        return Band.GHZ_6
    if freq_mhz >= 5150:
        return Band.GHZ_5
    return Band.GHZ_2_4


def _channel_from_freq(freq_mhz: int) -> int:
    if freq_mhz == 2484:
        return 14
    if 2412 <= freq_mhz <= 2472:
        return (freq_mhz - 2407) // 5
    if 5170 <= freq_mhz <= 5885:
        return (freq_mhz - 5000) // 5
    if 5925 <= freq_mhz <= 7115:
        return (freq_mhz - 5950) // 5
    return 0


def read_local_mac_address() -> str:
    system = platform.system()
    mac: str | None = None

    if system == "Linux":
        mac = _read_linux_mac()
    elif system == "Windows":
        mac = _read_windows_mac()
    elif system == "Darwin":
        mac = _read_macos_mac()

    return mac or _mac_from_uuid_getnode()


def _read_linux_mac() -> str | None:
    iface = _active_wifi_iface()
    if not iface:
        return None
    try:
        with open(f"/sys/class/net/{iface}/address") as f:
            return f.read().strip().upper()
    except OSError:
        return None


def _read_windows_mac() -> str | None:
    output = _run(["netsh", "wlan", "show", "interfaces"])
    if not output:
        return None
    match = re.search(r"Physical address\s*:\s*([0-9A-Fa-f:-]+)", output)
    if not match:
        return None
    return match.group(1).replace("-", ":").upper()


def _read_macos_mac() -> str | None:
    output = _run(["ifconfig", "en0"])
    if not output:
        return None
    match = re.search(r"ether\s+([0-9a-fA-F:]+)", output)
    if not match:
        return None
    return match.group(1).upper()


def _mac_from_uuid_getnode() -> str:
    node = uuid.getnode()
    return ":".join(f"{(node >> shift) & 0xff:02X}" for shift in range(40, -8, -8))