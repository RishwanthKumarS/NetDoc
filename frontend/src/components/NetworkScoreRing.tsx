import { scoreColor } from "../utils/networkScore";
import "./NetworkScoreRing.css";

interface NetworkScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

export function NetworkScoreRing({ score, size = 56, strokeWidth = 5 }: NetworkScoreRingProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);
  const color = scoreColor(clamped);

  return (
    <div
      className="network-score-ring"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Network score ${clamped} out of 100`}
      title={`Network score: ${clamped}/100`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          className="network-score-ring__track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="network-score-ring__fill"
        />
      </svg>
      <span className="network-score-ring__value" style={{ color }}>
        {clamped}
      </span>
    </div>
  );
}