import { useEffect, useState } from "react";
import { fetchDeviceAdvice } from "../api/client";
import "./FixModal.css";

interface FixModalProps {
  deviceId: string;
  deviceName: string;
  onClose: () => void;
}

export function FixModal({ deviceId, deviceName, onClose }: FixModalProps) {
  const [advice, setAdvice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
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
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Groq replies as a plain numbered list; split into lines rather than
  // pulling in a markdown parser for something this simple.
  const steps = advice
    ? advice
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
    : [];

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
          {loading && <p className="fix-modal__status">Asking Llama for troubleshooting steps…</p>}
          {error && <p className="fix-modal__error">Couldn't get advice: {error}</p>}
          {!loading && !error && (
            <ol className="fix-modal__steps">
              {steps.map((step, index) => (
                <li key={index}>{step.replace(/^\d+[.)]\s*/, "")}</li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}