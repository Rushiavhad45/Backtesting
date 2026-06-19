import React from "react";

function fmtPct(v) {
  return `${v > 0 ? "+" : ""}${v}%`;
}

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;

  const cards = [
    { label: "Final Equity", value: `Rs. ${metrics.final_equity.toLocaleString("en-IN")}`, cls: "" },
    { label: "Total Return", value: fmtPct(metrics.total_return_pct), cls: metrics.total_return_pct >= 0 ? "positive" : "negative" },
    { label: "CAGR", value: fmtPct(metrics.cagr_pct), cls: metrics.cagr_pct >= 0 ? "positive" : "negative" },
    { label: "Sharpe Ratio", value: metrics.sharpe_ratio, cls: "" },
    { label: "Max Drawdown", value: fmtPct(metrics.max_drawdown_pct), cls: "negative" },
  ];

  return (
    <div className="metrics-grid">
      {cards.map((c) => (
        <div className="metric-card" key={c.label}>
          <div className="label">{c.label}</div>
          <div className={`value ${c.cls}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}
