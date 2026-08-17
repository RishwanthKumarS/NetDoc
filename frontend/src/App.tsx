import { useEffect, useState } from "react";
import { useTelemetryStream } from "./hooks/useTelemetryStream";
import { Header } from "./components/Header";
import { DeviceTable } from "./components/DeviceTable";
import { DeviceDetail } from "./components/DeviceDetail";
import "./App.css";

export default function App() {
  const { devices, status } = useTelemetryStream();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // default to the first device once the first batch arrives, so the
  // detail panel isn't empty on load
  useEffect(() => {
    if (!selectedId && devices.length > 0) {
      setSelectedId(devices[0].device_id);
    }
  }, [devices, selectedId]);

  const selectedDevice = devices.find((d) => d.device_id === selectedId) ?? null;

  return (
    <div className="app">
      <div className="app__inner">
        <Header devices={devices} status={status} />
        <div className="app__layout">
          <DeviceTable devices={devices} selectedId={selectedId} onSelect={setSelectedId} />
          {selectedDevice && <DeviceDetail device={selectedDevice} />}
        </div>
      </div>
    </div>
  );
}
