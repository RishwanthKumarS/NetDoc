import type { Band } from "../types/device";
import { BAND_COLOR } from "./diagnosticMeta";
import "./BandSpectrum.css";

const ALL_BANDS: Band[] = ["2.4GHz", "5GHz", "6GHz"];

interface BandSpectrumProps {
  supportedBands: Band[];
  activeBand: Band;
}

/**
 * Three zones, one per band. A zone is filled and bright if the
 * device supports it, outlined and dim if it doesn't, and gets a
 * marker dot if the device is actually connected there right now.
 *
 * This is the fastest way to answer the problem statement's core
 * question at a glance: is this device on the best band it's capable
 * of, or is it settling for less.
 */
export function BandSpectrum({ supportedBands, activeBand }: BandSpectrumProps) {
  return (
    <div className="band-spectrum" role="img" aria-label={`Supports ${supportedBands.join(", ")}, active on ${activeBand}`}>
      {ALL_BANDS.map((band) => {
        const supported = supportedBands.includes(band);
        const active = band === activeBand;
        return (
          <div
            key={band}
            className={`band-spectrum__zone ${supported ? "is-supported" : "is-unsupported"}`}
            style={{ ["--zone-color" as string]: BAND_COLOR[band] }}
          >
            <span className="band-spectrum__label">{band.replace("GHz", "")}</span>
            {active && <span className="band-spectrum__marker" />}
          </div>
        );
      })}
    </div>
  );
}