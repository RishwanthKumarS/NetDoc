import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Device, HistoryPoint } from "../types/device";
import { fetchDeviceHistory } from "../api/client";
import { DiagnosticBadge } from "./DiagnosticBadge";
import { BandSpectrum } from "./BandSpectrum";
import { FixModal } from "./FixModal";
import "./DeviceDetail.css";

interface DeviceDetailProps {
  device: Device;
}

function computeYDomain(values: number[]): [number, number] {
  if (values.length === 0) return [-95, -25];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  const padding = Math.max(span * 0.25, 3);
  return [Math.floor(min - padding), Math.ceil(max + padding)];
}

export function DeviceDetail({ device }: DeviceDetailProps) {
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [fixModalOpen, setFixModalOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const points = await fetchDeviceHistory(device.device_id);
      if (!cancelled) setHistory(points);
    }

    load();
    const interval = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [device.device_id]);

  // close the modal if the person switches to a different device while it's open
  useEffect(() => {
    setFixModalOpen(false);
  }, [device.device_id]);

  const chartData = history.map((point) => ({
    time: new Date(point.timestamp * 1000).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" }),
    rssi: point.rssi_dbm,
    snr: point.snr_db,
  }));

  const yDomain = computeYDomain(chartData.flatMap((point) => [point.rssi, point.snr]));

  const { telemetry, capability, diagnostic } = device;

  return (
    <aside className="device-detail">
      <header className="device-detail__header">
        <div>
          <h2>{device.name}</h2>
          <p className="device-detail__mac">{device.mac_address}</p>
        </div>
        <DiagnosticBadge code={diagnostic.code} />
      </header>

      <section className="device-detail__section">
        <h3>Capability vs active connection</h3>
        <BandSpectrum supportedBands={capability.supported_bands} activeBand={telemetry.active_band} />
        <dl className="device-detail__facts">
          <div>
            <dt>Max standard</dt>
            <dd>{capability.max_standard}</dd>
          </div>
          <div>
            <dt>Active standard</dt>
            <dd>{telemetry.active_standard}</dd>
          </div>
          <div>
            <dt>Channel width</dt>
            <dd>{capability.max_channel_width_mhz} MHz</dd>
          </div>
          <div>
            <dt>Capability source</dt>
            <dd>{capability.source.replace("_", " ")}</dd>
          </div>
        </dl>
      </section>

      <section className="device-detail__section">
        <h3>Signal history</h3>
        <div className="device-detail__chart">
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="var(--border-soft)" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
              <YAxis
                domain={yDomain}
                tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                axisLine={false}
                tickLine={false}
                width={34}
              />
              <Tooltip
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "var(--text-secondary)" }}
              />
              <Line type="monotone" dataKey="rssi" stroke="var(--band-5)" dot={false} strokeWidth={2} name="RSSI (dBm)" />
              <Line type="monotone" dataKey="snr" stroke="var(--band-24)" dot={false} strokeWidth={1.5} name="SNR (dB)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="device-detail__section">
        <h3>Diagnosis</h3>
        <p className="device-detail__summary">{diagnostic.summary}</p>
        <p className="device-detail__detail">{diagnostic.detail}</p>
        {diagnostic.estimated_distance_m !== null && (
          <p className="device-detail__distance">
            Estimated distance from the router: ~{diagnostic.estimated_distance_m.toFixed(1)} m
          </p>
        )}
        {diagnostic.code !== "GOOD" && (
          <button className="device-detail__fix-btn" onClick={() => setFixModalOpen(true)}>
            Fix ✨
          </button>
        )}
      </section>

      {fixModalOpen && (
        <FixModal deviceId={device.device_id} deviceName={device.name} onClose={() => setFixModalOpen(false)} />
      )}
    </aside>
  );
}