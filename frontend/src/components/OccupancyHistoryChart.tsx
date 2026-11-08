import type { OccupancyHistoryPoint } from "../api/occupancy";

type Props = {
  history: OccupancyHistoryPoint[];
  selectedTimestamp: number | null;
  onSelectTimestamp: (timestamp: number) => void;
};

const SERIES = [
  { key: "available", label: "Available", color: "#22c55e" },
  { key: "occupied", label: "Occupied", color: "#ef4444" },
  { key: "unknown", label: "Unknown", color: "#f59e0b" },
] as const;

export default function OccupancyHistoryChart({
  history,
  selectedTimestamp,
  onSelectTimestamp,
}: Props) {
  if (history.length === 0) {
    return <p>No historical occupancy data available.</p>;
  }

  const width = 900;
  const height = 300;
  const margin = { top: 20, right: 20, bottom: 40, left: 45 };

  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const maxTime = Math.max(...history.map((point) => point.timestamp_seconds));
  const maxCount = Math.max(1, ...history.map((point) => point.total));

  const x = (time: number) =>
    margin.left + (maxTime > 0 ? (time / maxTime) * plotWidth : 0);

  const y = (count: number) =>
    margin.top + plotHeight - (count / maxCount) * plotHeight;

  const pathFor = (key: "available" | "occupied" | "unknown") =>
    history
      .map((point, index) => {
        const command = index === 0 ? "M" : "L";
        return `${command} ${x(point.timestamp_seconds)} ${y(point[key])}`;
      })
      .join(" ");

  return (
    <div className="history-chart">
      <div
        className="history-chart-legend"
        style={{ display: "flex", gap: 20, marginBottom: 12 }}
      >
        {SERIES.map((series) => (
          <span key={series.key} style={{ color: series.color }}>
            ● {series.label}
          </span>
        ))}
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Historical parking occupancy over recorded video time"
        style={{ width: "100%", height: "auto" }}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
          const count = fraction * maxCount;
          const position = y(count);

          return (
            <g key={fraction}>
              <line
                x1={margin.left}
                y1={position}
                x2={width - margin.right}
                y2={position}
                stroke="#334155"
                strokeDasharray="4 4"
              />
              <text
                x={margin.left - 10}
                y={position + 4}
                fill="#94a3b8"
                fontSize="12"
                textAnchor="end"
              >
                {Math.round(count)}
              </text>
            </g>
          );
        })}

        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
          <text
            key={fraction}
            x={margin.left + fraction * plotWidth}
            y={height - 12}
            fill="#94a3b8"
            fontSize="12"
            textAnchor="middle"
          >
            {(fraction * maxTime).toFixed(1)}s
          </text>
        ))}

        {SERIES.map((series) => (
          <path
            key={series.key}
            d={pathFor(series.key)}
            fill="none"
            stroke={series.color}
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {selectedTimestamp !== null && (
          <line
            x1={x(selectedTimestamp)}
            y1={margin.top}
            x2={x(selectedTimestamp)}
            y2={margin.top + plotHeight}
            stroke="#e2e8f0"
            strokeWidth={1.5}
            strokeDasharray="5 4"
            pointerEvents="none"
          />
        )}

        {history.map((point) => {
          const selected = point.timestamp_seconds === selectedTimestamp;

          return (
            <g
              key={point.timestamp_seconds}
              role="button"
              tabIndex={0}
              aria-label={`Select occupancy at ${point.timestamp_seconds.toFixed(3)} seconds`}
              aria-pressed={selected}
              onClick={() => onSelectTimestamp(point.timestamp_seconds)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectTimestamp(point.timestamp_seconds);
                }
              }}
              style={{ cursor: "pointer", outline: "none" }}
            >
              <circle
                cx={x(point.timestamp_seconds)}
                cy={y(point.occupied)}
                r={12}
                fill="transparent"
              />
              <circle
                cx={x(point.timestamp_seconds)}
                cy={y(point.occupied)}
                r={selected ? 6 : 3.5}
                fill={selected ? "#ffffff" : "#ef4444"}
                stroke={selected ? "#ef4444" : "none"}
                strokeWidth={2}
              />
              <title>
                {`${point.timestamp_seconds.toFixed(3)}s — ${point.available} available, ${point.occupied} occupied, ${point.unknown} unknown`}
              </title>
            </g>
          );
        })}
      </svg>

      <p>
        Select a marker to inspect occupancy at that recorded timestamp.
      </p>
    </div>
  );
}
