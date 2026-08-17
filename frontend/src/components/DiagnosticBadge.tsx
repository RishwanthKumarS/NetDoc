import type { DiagnosticCode } from "../types/device";
import { DIAGNOSTIC_META } from "./diagnosticMeta";
import "./DiagnosticBadge.css";

export function DiagnosticBadge({ code }: { code: DiagnosticCode }) {
  const meta = DIAGNOSTIC_META[code];
  return (
    <span className="diagnostic-badge" style={{ ["--badge-color" as string]: meta.color }}>
      <span className="diagnostic-badge__dot" />
      {meta.label}
    </span>
  );
}