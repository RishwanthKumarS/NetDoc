"""
Calls Groq's OpenAI-compatible chat completions endpoint to turn a
device's diagnosis into plain-language troubleshooting steps. Groq is
a hosted API, not something that runs locally -- this just makes an
outbound HTTPS call to it, so it behaves identically whether the
backend itself is on localhost or deployed. Requires GROQ_API_KEY to
be set in the environment; get a free key from
https://console.groq.com/keys.
"""

from __future__ import annotations

import os

import httpx

from app.models import Device

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"

class AdviceError(Exception):
    pass


def _build_prompt(device: Device) -> str:
    t = device.telemetry
    c = device.capability
    d = device.diagnostic

    distance = f"~{d.estimated_distance_m} m" if d.estimated_distance_m is not None else "unknown"

    return f"""A Wi-Fi diagnostic tool flagged a connected device with a problem. Give short, practical troubleshooting advice a home user could actually follow.

Device: {device.name} ({device.vendor})
Diagnosis: {d.summary} — {d.detail}
Estimated distance from router: {distance}

Capability: max standard {c.max_standard}, supports {', '.join(c.supported_bands)}, max channel width {c.max_channel_width_mhz} MHz
Currently connected: {t.active_standard} on {t.active_band}, channel {t.channel}
Signal: {t.rssi_dbm} dBm RSSI, {t.snr_db:.1f} dB SNR
Link rate: {t.link_rate_mbps:.0f} Mbps of a theoretical {t.theoretical_max_mbps:.0f} Mbps
Retry rate: {t.retry_rate_pct:.1f}%, packet loss: {t.packet_loss_pct:.1f}%

Reply with 3-5 short, concrete steps as a numbered list. No preamble, no summary at the end, just the steps."""


async def get_troubleshooting_advice(device: Device) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise AdviceError(
            "GROQ_API_KEY is not set. Get a free key from https://console.groq.com/keys "
            "and add it to backend/.env as GROQ_API_KEY=..."
        )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise home-networking troubleshooting assistant."},
            {"role": "user", "content": _build_prompt(device)},
        ],
        "temperature": 0.4,
        "max_tokens": 400,
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
    except httpx.RequestError as exc:
        raise AdviceError(f"Could not reach Groq: {exc}") from exc

    if response.status_code != 200:
        raise AdviceError(f"Groq returned {response.status_code}: {response.text[:300]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise AdviceError("Unexpected response shape from Groq") from exc