export function MetricBadge({ label, value, hint, large }) {
  return (
    <div className={`metric-badge${large ? " large" : ""}`}>
      <span className="metric-badge-label">{label}</span>
      <span className="metric-badge-value">{value}</span>
      {hint && <span className="metric-badge-hint">{hint}</span>}
    </div>
  );
}
