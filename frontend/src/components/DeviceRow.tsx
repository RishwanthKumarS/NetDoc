import type { Device } from "../types/device";
import { BandSpectrum } from "./BandSpectrum";
import { SignalMeter } from "./SignalMeter";
import { DiagnosticBadge } from "./DiagnosticBadge";
import "./DeviceRow.css";

interface DeviceRowProps {
  device: Device;
  onSelect: () => void;
  selected: boolean;
}

export function DeviceRow({ device, onSelect, selected }: DeviceRowProps) {
  const { telemetry, capability, diagnostic } = device;
  const snr = telemetry.rssi_dbm - telemetry.noise_floor_dbm;
  const rateShare = Math.round((telemetry.link_rate_mbps / telemetry.theoretical_max_mbps) * 100);
  const rateMBps = (telemetry.link_rate_mbps / 8).toFixed(1);

  return (
    <button className={`device-row ${selected ? "is-selected" : ""}`} onClick={onSelect}>
      <div className="device-row__identity">
        <span className="device-row__name">
          {device.name}
          {device.is_real ? (
            <span className="device-row__live-tag">live</span>
          ) : (
            <span className="device-row__demo-tag">demo</span>
          )}
        </span>
        <span className="device-row__meta">
          {device.vendor} &middot; {capability.max_standard}
        </span>
      </div>

      <div className="device-row__field" data-label="Band capability">
        <BandSpectrum supportedBands={capability.supported_bands} activeBand={telemetry.active_band} />
      </div>

      <div className="device-row__field" data-label="Signal">
        <SignalMeter rssiDbm={telemetry.rssi_dbm} snrDb={snr} />
      </div>

      <div className="device-row__field" data-label="Link rate">
        <div className="device-row__rate">
          <span className="device-row__rate-value" title={`${rateMBps} MB/s`}>
            {telemetry.link_rate_mbps.toFixed(0)} Mbps
          </span>
          <span className="device-row__rate-share">{rateShare}% of {telemetry.theoretical_max_mbps.toFixed(0)}</span>
        </div>
      </div>

      <div className="device-row__field" data-label="Diagnosis">
        <DiagnosticBadge code={diagnostic.code} />
      </div>
    </button>
  );
}