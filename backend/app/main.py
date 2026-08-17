"""
Entry point. Wires the simulator and the real-device tap into a small
FastAPI app, and pushes updates to the dashboard over a WebSocket
every couple of seconds. REST endpoints exist for a first page load
and for pulling a single device's chart history.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.capability import resolve_from_catalog
from app.diagnostics import diagnose
from app.local_wifi import read_local_adapter_state
from app.models import Band, CapabilityProfile, Device, TelemetrySample, WifiStandard
from app.rate_tables import theoretical_max_mbps
from app.simulator import NOISE_FLOOR_DBM, TelemetrySimulator
from app.store import get_connection, get_history, prune_old_samples, record_sample

app = FastAPI(title="Wi-Fi Band Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a local hackathon demo, would be scoped down for anything real
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator = TelemetrySimulator()
db_conn = get_connection()

TICK_SECONDS = 2
LOCAL_DEVICE_ID = "local-laptop"
LOCAL_MAC = "AA:BB:CC:11:22:33"  # placeholder, we don't read the real MAC to keep this demo-safe


def _build_local_device() -> Device | None:
    """
    Turns whatever the host OS reports about its own Wi-Fi adapter
    into a Device, using the same shape as everything the simulator
    produces. Returns None if we're running somewhere with no wireless
    adapter to read (which, during judging on a shared container, is
    the common case, and is exactly why the simulator exists).
    """
    state = read_local_adapter_state()
    if state is None:
        return None

    band: Band = state["band"]
    # we don't have a real Wi-Fi standard from these OS commands without
    # deeper platform-specific parsing, so we assume Wi-Fi 6 on 5/6 GHz
    # and Wi-Fi 4 on 2.4 GHz as a reasonable stand-in for a modern laptop
    standard = WifiStandard.WIFI_6 if band != Band.GHZ_2_4 else WifiStandard.WIFI_4
    capability = CapabilityProfile(
        max_standard=standard,
        supported_bands=[Band.GHZ_2_4, Band.GHZ_5],
        max_channel_width_mhz=80,
        max_spatial_streams=2,
        source="oui_fallback",
    )
    theoretical = theoretical_max_mbps(standard, capability.max_channel_width_mhz, capability.max_spatial_streams)
    sample = TelemetrySample(
        device_id=LOCAL_DEVICE_ID,
        timestamp=time.time(),
        active_band=band,
        active_standard=standard,
        channel=state["channel"],
        rssi_dbm=state["rssi_dbm"],
        noise_floor_dbm=NOISE_FLOOR_DBM,
        link_rate_mbps=state["link_rate_mbps"],
        theoretical_max_mbps=theoretical,
        retry_rate_pct=0.0,
        packet_loss_pct=0.0,
    )
    verdict = diagnose(capability, sample)
    return Device(
        device_id=LOCAL_DEVICE_ID,
        name="This laptop",
        vendor="local adapter",
        mac_address=LOCAL_MAC,
        is_real=True,
        capability=capability,
        telemetry=sample,
        diagnostic=verdict,
    )


def collect_devices() -> list[Device]:
    devices = simulator.tick()
    local_device = _build_local_device()
    if local_device:
        devices.insert(0, local_device)

    for device in devices:
        record_sample(
            db_conn,
            device.device_id,
            device.telemetry.rssi_dbm,
            device.telemetry.snr_db,
            device.telemetry.link_rate_mbps,
            device.diagnostic.code.value,
        )
    prune_old_samples(db_conn)
    return devices


@app.get("/api/devices")
def get_devices() -> list[Device]:
    return collect_devices()


@app.get("/api/devices/{device_id}/history")
def get_device_history(device_id: str, limit: int = 200) -> list[dict]:
    return get_history(db_conn, device_id, limit)


@app.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            devices = collect_devices()
            payload = [device.model_dump(mode="json") for device in devices]
            await websocket.send_json(payload)
            await asyncio.sleep(TICK_SECONDS)
    except WebSocketDisconnect:
        pass
