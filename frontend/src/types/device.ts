// These mirror app/models.py on the backend field for field. Keeping
// them in sync by hand is fine at this size, if the API grows past a
// handful of endpoints it'd be worth generating this from the FastAPI
// OpenAPI schema instead.

export type Band = "2.4GHz" | "5GHz" | "6GHz";

export type WifiStandard = "Wi-Fi 4" | "Wi-Fi 5" | "Wi-Fi 6" | "Wi-Fi 6E" | "Wi-Fi 7";

export type DiagnosticCode =
  | "GOOD"
  | "HARDWARE_LIMITED"
  | "BAND_STEERING_ISSUE"
  | "ATTENUATED_SIGNAL"
  | "FAR_DISTANCE"
  | "CONGESTED_LINK";

export interface CapabilityProfile {
  max_standard: WifiStandard;
  supported_bands: Band[];
  max_channel_width_mhz: number;
  max_spatial_streams: number;
  source: string;
}

export interface TelemetrySample {
  device_id: string;
  timestamp: number;
  active_band: Band;
  active_standard: WifiStandard;
  channel: number;
  rssi_dbm: number;
  noise_floor_dbm: number;
  link_rate_mbps: number;
  theoretical_max_mbps: number;
  retry_rate_pct: number;
  packet_loss_pct: number;
}

export interface DiagnosticResult {
  code: DiagnosticCode;
  summary: string;
  detail: string;
  estimated_distance_m: number | null;
}

export interface Device {
  device_id: string;
  name: string;
  vendor: string;
  mac_address: string;
  is_real: boolean;
  capability: CapabilityProfile;
  telemetry: TelemetrySample;
  diagnostic: DiagnosticResult;
}

export interface HistoryPoint {
  timestamp: number;
  rssi_dbm: number;
  snr_db: number;
  link_rate_mbps: number;
  diagnostic_code: DiagnosticCode;
}
