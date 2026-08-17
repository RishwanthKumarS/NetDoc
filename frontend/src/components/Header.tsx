import type { ConnectionStatus } from "../hooks/useTelemetryStream";
import type { Band, Device } from "../types/device";
import { BAND_COLOR } from "./diagnosticMeta";
import "./Header.css";

interface HeaderProps {
  devices: Device[];
  status: ConnectionStatus;
}

const BANDS: Band[] = ["2.4GHz", "5GHz", "6GHz"];

export function Header({ devices, status }: HeaderProps) {
  const counts = BANDS.map((band) => ({
    band,
    count: devices.filter((d) => d.telemetry.active_band === band).length,
  }));
  const flaggedCount = devices.filter((d) => d.diagnostic.code !== "GOOD").length;

  return (
    <header className="app-header">
      <div className="app-header__title">
        <h1>Wi-Fi Band Analyzer</h1>
        <p>Watching {devices.length} clients across 2.4, 5 and 6 GHz</p>
      </div>

      <div className="app-header__distribution">
        {counts.map(({ band, count }) => (
          <div key={band} className="app-header__band-count">
            <span className="app-header__band-dot" style={{ background: BAND_COLOR[band] }} />
            <span>{band}</span>
            <span className="app-header__band-value">{count}</span>
          </div>
        ))}
      </div>

      <div className="app-header__status">
        {flaggedCount > 0 && <span className="app-header__flag">{flaggedCount} flagged</span>}
        <span className={`app-header__connection is-${status}`}>
          <span className="app-header__connection-dot" />
          {status === "live" ? "Live" : status === "connecting" ? "Connecting" : "Reconnecting"}
        </span>
      </div>
    </header>
  );
}
