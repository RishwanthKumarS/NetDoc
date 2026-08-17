"""
Data models for the whole backend.

Everything else in the app (simulator, diagnostics engine, API routes)
passes these objects around, so this file is the single source of truth
for what a "device" and a "telemetry sample" look like.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Band(str, Enum):
    GHZ_2_4 = "2.4GHz"
    GHZ_5 = "5GHz"
    GHZ_6 = "6GHz"


class WifiStandard(str, Enum):
    WIFI_4 = "Wi-Fi 4"   # 802.11n
    WIFI_5 = "Wi-Fi 5"   # 802.11ac
    WIFI_6 = "Wi-Fi 6"   # 802.11ax on 2.4/5 GHz
    WIFI_6E = "Wi-Fi 6E"  # 802.11ax with 6 GHz support
    WIFI_7 = "Wi-Fi 7"   # 802.11be


class DiagnosticCode(str, Enum):
    GOOD = "GOOD"
    HARDWARE_LIMITED = "HARDWARE_LIMITED"
    BAND_STEERING_ISSUE = "BAND_STEERING_ISSUE"
    ATTENUATED_SIGNAL = "ATTENUATED_SIGNAL"
    FAR_DISTANCE = "FAR_DISTANCE"
    CONGESTED_LINK = "CONGESTED_LINK"


class CapabilityProfile(BaseModel):
    """
    What a device is theoretically capable of. This is the "on paper"
    side of the comparison, either read from a real device catalog entry,
    parsed from association-frame Information Elements, or guessed from
    the MAC OUI as a last resort.
    """

    max_standard: WifiStandard
    supported_bands: list[Band]
    max_channel_width_mhz: int
    max_spatial_streams: int
    source: str = Field(
        description="Where this profile came from: 'catalog', 'ie_parse', or 'oui_fallback'"
    )


class TelemetrySample(BaseModel):
    """
    A single point-in-time reading for a connected client. This is the
    "actually happening right now" side of the comparison.
    """

    device_id: str
    timestamp: float
    active_band: Band
    active_standard: WifiStandard
    channel: int
    rssi_dbm: float
    noise_floor_dbm: float
    link_rate_mbps: float
    theoretical_max_mbps: float
    retry_rate_pct: float
    packet_loss_pct: float

    @property
    def snr_db(self) -> float:
        return self.rssi_dbm - self.noise_floor_dbm


class DiagnosticResult(BaseModel):
    code: DiagnosticCode
    summary: str
    detail: str
    estimated_distance_m: Optional[float] = None


class Device(BaseModel):
    """
    Everything the dashboard needs for one row in the device table:
    identity, what it's capable of, what it's doing right now, and
    what the diagnostic engine thinks about it.
    """

    device_id: str
    name: str
    vendor: str
    mac_address: str
    is_real: bool = Field(
        default=False,
        description="True for the one device we read from the host laptop's own Wi-Fi adapter",
    )
    capability: CapabilityProfile
    telemetry: TelemetrySample
    diagnostic: DiagnosticResult
