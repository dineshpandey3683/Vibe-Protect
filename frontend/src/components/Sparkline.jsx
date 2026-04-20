import React from "react";

/**
 * Sparkline — dependency-free inline SVG line chart.
 *
 * Renders `data` (array of numbers) as a polyline across `width` × `height`.
 * Auto-scales to the min/max of the series with a 5% vertical padding so a
 * flat line doesn't hug the edge.
 *
 * Renders nothing if fewer than 2 points are supplied — a single datum is
 * not a trend, and rendering it as a dot would be more noise than signal.
 *
 * Props
 * -----
 *   data           number[]              series to plot
 *   width, height  number                SVG box (default 80×24)
 *   stroke         string                line colour (default emerald)
 *   dashed         boolean               dash seed-origin entries
 *   seedMask       boolean[] | undefined mask flagging which indices were
 *                                        seeded (not real CI runs). Seeded
 *                                        prefix is drawn dashed; any real
 *                                        runs are drawn solid.
 *   title          string                a11y <title> / tooltip
 */
export default function Sparkline({
  data,
  width = 80,
  height = 24,
  stroke = "#22c55e",
  seedMask,
  title = "",
}) {
  if (!data || data.length < 2) return null;

  const lo = Math.min(...data);
  const hi = Math.max(...data);
  const range = hi - lo || 1;
  const pad = height * 0.1;
  const yOf = (v) => height - pad - ((v - lo) / range) * (height - 2 * pad);
  const xOf = (i) => (i / (data.length - 1)) * width;

  const pts = data.map((v, i) => [xOf(i), yOf(v)]);
  const pathD = "M " + pts.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(" L ");

  // Split seeded prefix (if any) from the real-CI tail so they render with
  // different stroke styles. A series with NO seeded entries just renders
  // solid end-to-end.
  let seedPath = null;
  let realPath = pathD;
  if (seedMask && seedMask.some((s) => s)) {
    const lastSeed = seedMask.lastIndexOf(true);
    if (lastSeed >= 0 && lastSeed < data.length - 1) {
      const head = pts.slice(0, lastSeed + 1);
      const tail = pts.slice(lastSeed);   // overlap one point so they join
      seedPath = "M " + head.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(" L ");
      realPath = "M " + tail.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(" L ");
    } else if (lastSeed === data.length - 1) {
      // everything is seeded — whole line is dashed
      seedPath = pathD;
      realPath = null;
    }
  }

  const [lx, ly] = pts[pts.length - 1];
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={title}
      className="overflow-visible"
    >
      {title ? <title>{title}</title> : null}
      {seedPath && (
        <path
          d={seedPath}
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
          strokeOpacity="0.55"
          strokeDasharray="2 2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {realPath && (
        <path
          d={realPath}
          fill="none"
          stroke={stroke}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      <circle cx={lx} cy={ly} r="2" fill={stroke} />
    </svg>
  );
}
