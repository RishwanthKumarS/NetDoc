"""
Synthetic telemetry engine.

We don't have a router or an AP to pull real client stats from, so
this stands in for that data source. It keeps a small population of
virtual clients alive, walks their RSSI around realistically every
tick, and occasionally scripts an event (someone walks to another
room, a device sits behind a wall, and so on) so the diagnostic engine
has real cases to catch during a live demo instead of just flat numbers.

The important thing here is that nothing downstream of this file knows
or cares that the data is synthetic. It produces the exact same
TelemetrySample shape that a real hostapd/iw poll would, so swapping
in a real data source later only means replacing this file.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from app.capability import resolve_from_catalog
from app.device_catalog import DEVICE_CATALOG, CatalogEntry
from app.models import Band, CapabilityProfile, Device, TelemetrySample, WifiStandard
from app.pathloss import expected_rssi_at_distance
from app.rate_tables import theoretical_max_mbps
from app.diagnostics import diagnose

NOISE_FLOOR_DBM = -95.0  # typical indoor noise floor, used as a constant since we can't measure it live


@dataclass
class VirtualClient:
    entry: CatalogEntry
    device_id: str
    distance_m: float
    wall_loss_db: float
    active_band: Band
    channel_width_mhz: int
    congestion_level: float  # 0 = clear air, 1 = heavily contested
    scenario: str = "steady"
    _rssi_dbm: float = field(default=-55.0)

    def initial_band(self) -> Band:
        # devices default to their best band unless a scenario says otherwise
        band_order = {Band.GHZ_2_4: 0, Band.GHZ_5: 1, Band.GHZ_6: 2}
        return max(self.entry.capability.supported_bands, key=lambda b: band_order[b])

    def tick(self) -> TelemetrySample:
        # move the distance a little each tick for the "walking away" and
        # "walking back" scenarios, otherwise stay put
        if self.scenario == "walking_away":
            self.distance_m = min(self.distance_m + 0.6, 27.0)
        elif self.scenario == "walking_back":
            self.distance_m = max(self.distance_m - 0.6, 1.0)

        target_rssi = expected_rssi_at_distance(self.active_band, self.distance_m, self.wall_loss_db)
        # random walk toward the target instead of snapping to it, so the
        # line chart looks like a real noisy signal rather than a staircase
        self._rssi_dbm += (target_rssi - self._rssi_dbm) * 0.3 + random.uniform(-1.2, 1.2)

        standard = self.entry.capability.max_standard
        streams = self.entry.capability.max_spatial_streams
        theoretical = theoretical_max_mbps(standard, self.channel_width_mhz, streams)

        # worse SNR and higher congestion both eat into how much of the
        # theoretical rate actually gets used
        snr = self._rssi_dbm - NOISE_FLOOR_DBM
        snr_factor = max(0.05, min(1.0, (snr - 5) / 35))
        congestion_factor = 1.0 - (self.congestion_level * 0.6)
        link_rate = theoretical * snr_factor * congestion_factor
        link_rate *= random.uniform(0.92, 1.05)
        link_rate = max(1.0, min(link_rate, theoretical))

        # multipath fading gets worse the further a client is from the AP,
        # on top of whatever congestion is doing to it. a device sitting
        # behind a single wall at short range doesn't get this penalty,
        # which is what lets the diagnostic engine tell "blocked but
        # close" apart from "genuinely far" further down the pipeline
        multipath_retry = max(0.0, (self.distance_m - 8.0) * 1.5)
        retry_rate = max(0.0, self.congestion_level * 25 + multipath_retry + random.uniform(-2, 4))
        packet_loss = max(0.0, retry_rate * 0.15 + random.uniform(-0.5, 0.5))

        return TelemetrySample(
            device_id=self.device_id,
            timestamp=time.time(),
            active_band=self.active_band,
            active_standard=standard,
            channel=_channel_for_band(self.active_band),
            rssi_dbm=round(self._rssi_dbm, 1),
            noise_floor_dbm=NOISE_FLOOR_DBM,
            link_rate_mbps=round(link_rate, 1),
            theoretical_max_mbps=theoretical,
            retry_rate_pct=round(retry_rate, 1),
            packet_loss_pct=round(packet_loss, 2),
        )


def _channel_for_band(band: Band) -> int:
    return {Band.GHZ_2_4: 6, Band.GHZ_5: 44, Band.GHZ_6: 37}[band]


def _make_mac(prefix: str, index: int) -> str:
    tail = f"{index:06X}"
    return f"{prefix}:{tail[0:2]}:{tail[2:4]}:{tail[4:6]}"


# Scripted scenarios, picked to guarantee the demo shows every
# diagnostic category at least once instead of leaving it to chance.
_SCENARIO_PLAN = [
    # (catalog index, distance_m, wall_loss_db, band override, congestion, scenario)
    (0, 4.0, 0.0, None, 0.5, "steady"),               # iPhone, close, clean -> GOOD
    (1, 6.0, 0.0, None, 0.1, "steady"),                 # MacBook, close, clean -> GOOD
    (2, 3.0, 0.0, Band.GHZ_2_4, 0.05, "steady"),        # Galaxy S24, capable of 6GHz but parked on 2.4 -> BAND_STEERING
    (3, 5.0, 0.0, None, 0.75, "steady"),                # ThinkPad, good signal, congested air -> CONGESTED_LINK
    (4, 3.0, 0.0, None, 0.05, "steady"),                # Echo Dot, 2.4GHz only hardware -> HARDWARE_LIMITED
    (5, 8.0, 18.0, None, 0.1, "steady"),                # budget Galaxy, close but heavy wall loss -> ATTENUATED_SIGNAL
    (6, 3.0, 0.0, None, 0.05, "steady"),                # printer, 2.4GHz only -> HARDWARE_LIMITED
    (7, 14.0, 0.0, None, 0.1, "walking_away"),          # Nest Cam, actually far and getting farther -> FAR_DISTANCE
    (8, 5.0, 0.0, None, 0.05, "steady"),                # Pixel 8, close and clean -> GOOD
    (9, 3.0, 0.0, None, 0.05, "steady"),                # old tablet, 2.4GHz only -> HARDWARE_LIMITED
]


def build_virtual_clients() -> list[VirtualClient]:
    clients = []
    for i, (catalog_idx, distance, wall_loss, band_override, congestion, scenario) in enumerate(_SCENARIO_PLAN):
        entry = DEVICE_CATALOG[catalog_idx]
        client = VirtualClient(
            entry=entry,
            device_id=f"sim-{i}",
            distance_m=distance,
            wall_loss_db=wall_loss,
            active_band=band_override or _best_band(entry.capability),
            channel_width_mhz=entry.capability.max_channel_width_mhz,
            congestion_level=congestion,
            scenario=scenario,
        )
        clients.append(client)
    return clients


def _best_band(capability: CapabilityProfile) -> Band:
    band_order = {Band.GHZ_2_4: 0, Band.GHZ_5: 1, Band.GHZ_6: 2}
    return max(capability.supported_bands, key=lambda b: band_order[b])


class TelemetrySimulator:
    """
    Owns the population of virtual clients and produces a fresh batch
    of Device objects (capability + telemetry + diagnostic, all
    resolved) every time tick() is called.
    """

    def __init__(self) -> None:
        self.clients = build_virtual_clients()

    def tick(self) -> list[Device]:
        devices = []
        for client in self.clients:
            sample = client.tick()
            capability = client.entry.capability
            mac = _make_mac(client.entry.mac_prefix, hash(client.device_id) % 999999)
            verdict = diagnose(capability, sample)
            devices.append(
                Device(
                    device_id=client.device_id,
                    name=client.entry.name,
                    vendor=client.entry.vendor,
                    mac_address=mac,
                    is_real=False,
                    capability=capability,
                    telemetry=sample,
                    diagnostic=verdict,
                )
            )
        return devices
