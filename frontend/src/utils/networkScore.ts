import type { Device } from "../types/device";

/**
 * Rolls telemetry into a single 0-100 "network score" so device
 * health can be read at a glance instead of cross-referencing four
 * separate numbers. Weighted toward signal quality and achieved
 * throughput, since those are what's actually felt day to day; retry
 * rate and packet loss pull the score down when the link is flaky
 * even if raw signal looks fine.
 */
export function computeNetworkScore(device: Device): number {
  const { telemetry } = device;
  const snr = telemetry.rssi_dbm - telemetry.noise_floor_dbm;

  const snrScore = clamp((snr / 40) * 100);
  const rateScore = clamp((telemetry.link_rate_mbps / telemetry.theoretical_max_mbps) * 100);
  const retryScore = clamp(100 - telemetry.retry_rate_pct * 2);
  const lossScore = clamp(100 - telemetry.packet_loss_pct * 10);

  const weighted = snrScore * 0.35 + rateScore * 0.35 + retryScore * 0.15 + lossScore * 0.15;

  return Math.round(clamp(weighted));
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, value));
}

/**
 * Red at 0, orange, yellow, then green at 100 -- interpolated as RGB
 * between stops so the ring shows shades within each band rather
 * than snapping between four flat colors.
 */
const SCORE_COLOR_STOPS: { score: number; rgb: [number, number, number] }[] = [
  { score: 0, rgb: [240, 85, 75] },    // red
  { score: 35, rgb: [240, 166, 61] },  // orange
  { score: 65, rgb: [234, 179, 8] },   // yellow
  { score: 100, rgb: [74, 222, 128] }, // green
];

export function scoreColor(score: number): string {
  const clamped = clamp(score);

  for (let i = 0; i < SCORE_COLOR_STOPS.length - 1; i++) {
    const a = SCORE_COLOR_STOPS[i];
    const b = SCORE_COLOR_STOPS[i + 1];
    if (clamped >= a.score && clamped <= b.score) {
      const t = (clamped - a.score) / (b.score - a.score);
      const rgb = a.rgb.map((channel, idx) => Math.round(channel + (b.rgb[idx] - channel) * t));
      return `rgb(${rgb.join(", ")})`;
    }
  }

  const last = SCORE_COLOR_STOPS[SCORE_COLOR_STOPS.length - 1];
  return `rgb(${last.rgb.join(", ")})`;
}