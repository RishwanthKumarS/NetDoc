import type { Device } from "../types/device";
import { DeviceRow } from "./DeviceRow";
import "./DeviceTable.css";

interface DeviceTableProps {
  devices: Device[];
  selectedId: string | null;
  onSelect: (deviceId: string) => void;
}

export function DeviceTable({ devices, selectedId, onSelect }: DeviceTableProps) {
  if (devices.length === 0) {
    return <p className="device-table__empty">Waiting for the first telemetry batch to come in.</p>;
  }

  return (
    <div className="device-table">
      <div className="device-table__header">
        <span>Device</span>
        <span>Band capability</span>
        <span>Signal</span>
        <span>Link rate</span>
        <span>Diagnosis</span>
      </div>
      <div className="device-table__rows">
        {devices.map((device) => (
          <DeviceRow
            key={device.device_id}
            device={device}
            selected={device.device_id === selectedId}
            onSelect={() => onSelect(device.device_id)}
          />
        ))}
      </div>
    </div>
  );
}