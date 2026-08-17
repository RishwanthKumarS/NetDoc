"""
Rough theoretical max PHY link rates per standard, channel width and
spatial stream count. These are simplified from the official 802.11
rate tables (we round to numbers that are close enough to be useful
for a diagnostic comparison, not a certification test).

The diagnostic engine uses this to answer "given what this device
negotiated, how fast should the link be" so it can tell a slow link
that's simply RF-limited apart from a device that never had a chance
to go fast in the first place.
"""

from app.models import WifiStandard

# Mbps per spatial stream at a representative MCS, keyed by
# (standard, channel_width_mhz). Multiply by spatial stream count.
_BASE_RATE_PER_STREAM: dict[tuple[WifiStandard, int], float] = {
    (WifiStandard.WIFI_4, 20): 72.2,
    (WifiStandard.WIFI_4, 40): 150.0,
    (WifiStandard.WIFI_5, 20): 86.7,
    (WifiStandard.WIFI_5, 40): 200.0,
    (WifiStandard.WIFI_5, 80): 433.3,
    (WifiStandard.WIFI_5, 160): 866.7,
    (WifiStandard.WIFI_6, 20): 143.4,
    (WifiStandard.WIFI_6, 40): 286.8,
    (WifiStandard.WIFI_6, 80): 600.4,
    (WifiStandard.WIFI_6, 160): 1200.8,
    (WifiStandard.WIFI_6E, 20): 143.4,
    (WifiStandard.WIFI_6E, 40): 286.8,
    (WifiStandard.WIFI_6E, 80): 600.4,
    (WifiStandard.WIFI_6E, 160): 1200.8,
    (WifiStandard.WIFI_7, 20): 180.4,
    (WifiStandard.WIFI_7, 40): 360.8,
    (WifiStandard.WIFI_7, 80): 755.2,
    (WifiStandard.WIFI_7, 160): 1510.4,
    (WifiStandard.WIFI_7, 320): 3020.8,
}


def theoretical_max_mbps(standard: WifiStandard, channel_width_mhz: int, spatial_streams: int) -> float:
    """
    Look up the closest supported width at or below the requested one
    (a device might negotiate a narrower channel than its max because
    of interference) and scale by stream count.
    """
    available_widths = sorted(w for (std, w) in _BASE_RATE_PER_STREAM if std == standard)
    usable_width = max((w for w in available_widths if w <= channel_width_mhz), default=available_widths[0])
    base_rate = _BASE_RATE_PER_STREAM[(standard, usable_width)]
    return round(base_rate * spatial_streams, 1)
