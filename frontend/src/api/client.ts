import type { HistoryPoint } from "../types/device";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function fetchDeviceHistory(deviceId: string): Promise<HistoryPoint[]> {
  const response = await fetch(`${API_URL}/api/devices/${deviceId}/history?limit=120`);
  if (!response.ok) {
    throw new Error(`history request failed: ${response.status}`);
  }
  return response.json();
}
