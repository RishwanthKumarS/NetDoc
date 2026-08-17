import { useEffect, useState } from "react";
import { fetchDeviceAdvice } from "../api/client";
import "./FixModal.css";

interface FixModalProps {
  deviceId: string;
  deviceName: string;
  onClose: () => void;
}

const CHARS_PER_TICK = 2;
const TICK_MS = 12;

export function FixModal({ deviceId, deviceName, onClose }: FixModalProps) {
  const [advice, setAdvice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [typedLength, setTypedLength] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setAdvice(null);
      setTypedLength(0);
      try {
        const result = await fetchDeviceAdvice(deviceId);
        if (!cancelled) setAdvice(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [deviceId]);

  useEffect(() => {
    if (!advice) return;
    setTypedLength(0);
    const interval = setInterval(() => {
      setTypedLength((prev) => {
        const next = prev + CHARS_PER_TICK;
        if (next >= advice.length) {
          clearInterval(interval);
          return advice.length;
        }
        return next;
      });
    }, TICK_MS);
    return () => clearInterval(interval);
  }, [advice]);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const isTyping = advice !== null && typedLength < advice.length;

  return (
    <div className="fix-modal__backdrop" onClick={onClose}>
      <div className="fix-modal" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <header className="fix-modal__header">
          <div>
            <p className="fix-modal__eyebrow">Fix ✨</p>
            <h2>{deviceName}</h2>
          </div>
          <button className="fix-modal__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="fix-modal__body">
          {loading && <p className="fix-modal__status">Asking NetDoc AI for troubleshooting steps…</p>}
          {error && <p className="fix-modal__error">Couldn't get advice: {error}</p>}
          {!loading && !error && advice && (
            <p className="fix-modal__typewriter">
              {advice.slice(0, typedLength)}
              {isTyping && <span className="fix-modal__cursor" />}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}