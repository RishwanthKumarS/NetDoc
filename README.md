# NetDoc - Wi-Fi Band Analyzer

NetDoc is a user-friendly dashboard that watches connected Wi-Fi clients,
compares what they're capable of against what they're actually getting,
and explains why any of them are underperforming, instead of just showing
raw signal numbers.

Built with no router or AP access. The data source is a synthetic telemetry
engine that behaves like a real network would, plus one real device pulled
from whatever laptop the backend runs on.

```
wifi-band-analyzer/
  backend/     Python + FastAPI, the analyzer itself
  frontend/    Vite + React + TypeScript, the dashboard
```

## Running it

Backend:

```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```
cd frontend
npm install
npm run dev
```

The dashboard expects the backend on `localhost:8000` by default. Copy
`frontend/.env.example` to `frontend/.env` to point it somewhere else.

## Architecture

```
┌─────────────────────────┐   ┌─────────────────────────────┐
│  Synthetic Telemetry    │   │  Local OS Wi-Fi Query       │
│  Simulator              │   │  (nmcli / netsh / wdutil)   │
│  backend/app/simulator  │   │  backend/app/local_wifi.py  │
└───────────┬─────────────┘   └─────────────┬───────────────┘
            │  10 virtual clients           │  this machine's real adapter
            │  scripted RSSI, retries,      │  RSSI, channel, link rate
            │  band, congestion             │
            └───────────────┬───────────────┘
                            ▼
                capability.py + device_catalog.py
                resolves what each device supports
                            ▼
                     diagnostics.py
              classifies why performance is what it is
                            ▼
                   main.py (FastAPI)
              REST for first load + device history
              WebSocket for the live feed, one tick every 2s
                            ▼
                  store.py (SQLite)
              keeps a 30 minute rolling history per device
                            ▼
                  React dashboard
        device table, band spectrum, signal meter, live chart
```

Nothing downstream of the simulator/local_wifi layer knows or cares that the
telemetry is synthetic. Both sources produce the exact same `TelemetrySample`
shape that a real `hostapd`/`iw` poll against a physical AP would, so
swapping in real router access later means replacing one file, not
rearchitecting the app.

## How each minimum requirement is met

**Client Capability Parsing.** `capability.py` has two paths. `parse_association_ie()`
reads actual 802.11 Information Element tags (HT/VHT/HE/EHT) the way you'd pull
them from a captured Association Request frame, and works out the standard and
band support from what's present, without knowing anything else about the
device. `resolve_from_catalog()` is the fallback path, a MAC OUI style lookup
against a local device catalog (`device_catalog.py`), used when frame capture
isn't available, which is the path the demo actually runs on.

**Real-Time Telemetry Ingestion.** The WebSocket at `/ws/telemetry` pushes a
fresh reading for every device every two seconds: active band, RSSI, SNR,
negotiated link rate, retry rate, packet loss. `simulator.py` generates this
for the virtual fleet, `local_wifi.py` reads the real figures for the host
machine's adapter, and both get folded into the same feed.

**Diagnostic Logic Engine.** `diagnostics.py`. Given a capability profile and a
telemetry sample, it works out one of six classifications: performing well,
hardware limited, connected below capability (band steering), signal blocked
by an obstruction, too far from the router, or congested air. The reasoning
behind each check, especially how it tells a wall apart from real distance
using retry-rate stability rather than RSSI alone, is documented inline in
that file since it's the core of the whole project.

**Visual Interface / Dashboard.** The React app renders a live device table
with a signature spectrum strip per device (capability vs active band at a
glance), a signal meter, and a color-coded diagnostic badge. Selecting a
device opens a detail panel with its full diagnosis and an RSSI/SNR history
chart pulled from the backend's SQLite store.

## Where this stands in for hardware we don't have

| Problem statement dependency | What we built instead |
|---|---|
| AP/router API access | `simulator.py`, architected behind the same data shape a real `hostapd`/`iw` integration would produce |
| 802.11k/v neighbor reports | Not implemented, noted as a real gap. Nothing in the four minimum requirements depends on it |
| Hardware fingerprint database | `device_catalog.py`, a local stand-in for an OUI/Wi-Fi Alliance registry |
| RF attenuation profiles | `pathloss.py`, the standard log-distance path loss model with published indoor exponents per band |
