import type { DiagnosticCode } from "../types/device";

interface DiagMeta {
  label: string;
  color: string;
}

// keeps the color and short label for each diagnostic code in one
// place instead of scattered across every component that shows one
export const DIAGNOSTIC_META: Record<DiagnosticCode, DiagMeta> = {
  GOOD: { label: "Performing well", color: "var(--diag-good)" },
  HARDWARE_LIMITED: { label: "Hardware limited", color: "var(--diag-hardware)" },
  BAND_STEERING_ISSUE: { label: "Below capability", color: "var(--diag-steering)" },
  ATTENUATED_SIGNAL: { label: "Signal blocked", color: "var(--diag-attenuated)" },
  FAR_DISTANCE: { label: "Too far", color: "var(--diag-far)" },
  CONGESTED_LINK: { label: "Congested", color: "var(--diag-congested)" },
};

export const BAND_COLOR: Record<string, string> = {
  "2.4GHz": "var(--band-24)",
  "5GHz": "var(--band-5)",
  "6GHz": "var(--band-6)",
};