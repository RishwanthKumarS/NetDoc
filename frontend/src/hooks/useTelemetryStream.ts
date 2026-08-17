import { useEffect, useRef, useState } from "react";
import type { Device } from "../types/device";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/telemetry";

// how long to wait before trying to reconnect after a dropped connection
const RECONNECT_DELAY_MS = 2000;

export type ConnectionStatus = "connecting" | "live" | "disconnected";

/**
 * Owns the WebSocket connection to the backend and keeps a live list
 * of devices in state. Reconnects on its own if the connection drops,
 * since a demo where the tab needs a manual refresh after the backend
 * hiccups is not a good look.
 */
export function useTelemetryStream() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => setStatus("live");

      socket.onmessage = (event) => {
        const payload: Device[] = JSON.parse(event.data);
        setDevices(payload);
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("disconnected");
        reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socketRef.current?.close();
    };
  }, []);

  return { devices, status };
}
