import { useEffect, useRef, useState } from "react";
import "./NetworkScoreInfo.css";

export function NetworkScoreInfo() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="network-score-info" ref={containerRef}>
      <button
        type="button"
        className="network-score-info__trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-label="How is the network score calculated?"
      >
        i
      </button>

      {open && (
        <div className="network-score-info__popover" role="dialog">
          <p className="network-score-info__title">Network score</p>
          <p className="network-score-info__body">
            A 0-100 rollup of link health, weighted across four telemetry values:
          </p>
          <ul className="network-score-info__list">
            <li><span className="network-score-info__weight">35%</span> Signal-to-noise ratio</li>
            <li><span className="network-score-info__weight">35%</span> Achieved vs. theoretical link rate</li>
            <li><span className="network-score-info__weight">15%</span> Retry rate</li>
            <li><span className="network-score-info__weight">15%</span> Packet loss</li>
          </ul>
          <p className="network-score-info__body">
            The ring runs green through yellow and orange to red as the score drops.
          </p>
        </div>
      )}
    </div>
  );
}