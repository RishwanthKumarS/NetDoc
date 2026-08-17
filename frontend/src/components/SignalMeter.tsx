import "./SignalMeter.css";

interface SignalMeterProps {
  rssiDbm: number;
  snrDb: number;
}

// -30 dBm is about as good as Wi-Fi gets, -90 dBm is basically gone.
// clamp into that range and turn it into a 0-1 fill so the bar reads
// intuitively without needing to know what a dBm is.
const RSSI_CEILING = -30;
const RSSI_FLOOR = -90;

function rssiToFill(rssiDbm: number): number {
  const clamped = Math.min(RSSI_CEILING, Math.max(RSSI_FLOOR, rssiDbm));
  return (clamped - RSSI_FLOOR) / (RSSI_CEILING - RSSI_FLOOR);
}

export function SignalMeter({ rssiDbm, snrDb }: SignalMeterProps) {
  const fill = rssiToFill(rssiDbm);
  const quality = fill > 0.66 ? "strong" : fill > 0.4 ? "fair" : "weak";

  return (
    <div className="signal-meter">
      <div className="signal-meter__bar">
        <div className={`signal-meter__fill is-${quality}`} style={{ width: `${fill * 100}%` }} />
      </div>
      <div className="signal-meter__figures">
        <span className="signal-meter__rssi">{rssiDbm.toFixed(0)} dBm</span>
        <span className="signal-meter__snr">{snrDb.toFixed(0)} dB SNR</span>
      </div>
    </div>
  );
}