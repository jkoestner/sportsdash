import { useId, useState, type PointerEvent } from "react";

interface Props {
  points: number[]; // home win %, 0-100
  homeAbbr: string;
  awayAbbr: string;
  live?: boolean;
}

const W = 600;
const H = 180;

/**
 * Win probability area chart in plain SVG (no chart library).
 * Above the dashed 50% line favors the home team, below favors the away team.
 * Hover or drag to read a value.
 */
export function WinProbChart({ points, homeAbbr, awayAbbr, live = false }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const gradId = useId();
  if (points.length < 2) return null;

  const x = (i: number) => (i / (points.length - 1)) * W;
  const y = (p: number) => H - (p / 100) * H;
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join("");
  const area = `${line}L${W},${H / 2}L0,${H / 2}Z`; // fill toward the 50% line

  function onMove(e: PointerEvent<SVGSVGElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const frac = (e.clientX - box.left) / box.width;
    setHover(Math.max(0, Math.min(points.length - 1, Math.round(frac * (points.length - 1)))));
  }

  const value = hover != null ? points[hover] : points[points.length - 1];
  const leader = value == null ? "" : value >= 50 ? `${homeAbbr} ${Math.round(value)}%` : `${awayAbbr} ${Math.round(100 - value)}%`;

  return (
    <figure className="wp">
      <div className="wp-axis" aria-hidden="true">
        <span>{homeAbbr}</span>
        <span>50%</span>
        <span>{awayAbbr}</span>
      </div>
      <div className="wp-plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`Win probability. ${live ? "Now" : "Final"}: ${leader}`}
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
        >
          <defs>
            <clipPath id={`${gradId}-top`}>
              <rect x="0" y="0" width={W} height={H / 2} />
            </clipPath>
            <clipPath id={`${gradId}-bot`}>
              <rect x="0" y={H / 2} width={W} height={H / 2} />
            </clipPath>
          </defs>
          <path d={area} className="wp-fill home" clipPath={`url(#${gradId}-top)`} />
          <path d={area} className="wp-fill away" clipPath={`url(#${gradId}-bot)`} />
          <line x1="0" x2={W} y1={H / 2} y2={H / 2} className="wp-mid" />
          <path d={line} className="wp-line" />
          {hover != null && <line x1={x(hover)} x2={x(hover)} y1="0" y2={H} className="wp-cursor" />}
        </svg>
        <figcaption className="wp-readout">{hover != null ? leader : `${live ? "Now" : "Final"}: ${leader}`}</figcaption>
      </div>
    </figure>
  );
}
