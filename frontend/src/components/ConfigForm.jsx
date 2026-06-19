import React from "react";

const METRIC_OPTIONS = [
  { value: "roe", label: "ROE" },
  { value: "roce", label: "ROCE" },
  { value: "pe_ratio", label: "PE Ratio" },
  { value: "pat_cr", label: "PAT" },
  { value: "revenue_cr", label: "Revenue" },
  { value: "market_cap_cr", label: "Market Cap" },
  { value: "debt_to_equity", label: "Debt to Equity" },
];

export default function ConfigForm({ config, setConfig, onRun, loading }) {
  const update = (key, value) => setConfig((prev) => ({ ...prev, [key]: value }));

  const updateRankMetric = (index, field, value) => {
    const updated = [...config.rank_metrics];
    updated[index] = { ...updated[index], [field]: value };
    update("rank_metrics", updated);
  };

  const addRankMetric = () => {
    update("rank_metrics", [...config.rank_metrics, { metric: "roe", direction: "desc" }]);
  };

  const removeRankMetric = (index) => {
    update("rank_metrics", config.rank_metrics.filter((_, i) => i !== index));
  };

  return (
    <div>
      <div className="section-title">Date Range</div>
      <div className="field-row">
        <div className="field-group">
          <label>Start Date</label>
          <input type="date" value={config.start_date} onChange={(e) => update("start_date", e.target.value)} />
        </div>
        <div className="field-group">
          <label>End Date</label>
          <input type="date" value={config.end_date} onChange={(e) => update("end_date", e.target.value)} />
        </div>
      </div>

      <div className="field-group">
        <label>Rebalance Frequency</label>
        <select value={config.rebalance_freq} onChange={(e) => update("rebalance_freq", e.target.value)}>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="yearly">Yearly</option>
        </select>
      </div>

      <div className="field-group">
        <label>Portfolio Size (top N stocks)</label>
        <input
          type="number"
          min="1"
          max="50"
          value={config.portfolio_size}
          onChange={(e) => update("portfolio_size", Number(e.target.value))}
        />
      </div>

      <div className="field-group">
        <label>Initial Capital (Rs.)</label>
        <input
          type="number"
          value={config.initial_capital}
          onChange={(e) => update("initial_capital", Number(e.target.value))}
        />
      </div>

      <div className="section-title">Position Sizing</div>
      <div className="field-group">
        <label>Method</label>
        <select value={config.position_sizing} onChange={(e) => update("position_sizing", e.target.value)}>
          <option value="equal">Equal Weighted</option>
          <option value="market_cap">Market Cap Weighted</option>
          <option value="metric">Metric Weighted</option>
        </select>
      </div>
      {config.position_sizing === "metric" && (
        <div className="field-group">
          <label>Sizing Metric</label>
          <select value={config.sizing_metric} onChange={(e) => update("sizing_metric", e.target.value)}>
            {METRIC_OPTIONS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
      )}

      <div className="section-title">Filters (applied once, used every rebalance)</div>
      <div className="field-row">
        <div className="field-group">
          <label>Min Market Cap (Cr)</label>
          <input type="number" value={config.min_market_cap} onChange={(e) => update("min_market_cap", Number(e.target.value))} />
        </div>
        <div className="field-group">
          <label>Max Market Cap (Cr)</label>
          <input type="number" value={config.max_market_cap} onChange={(e) => update("max_market_cap", Number(e.target.value))} />
        </div>
      </div>
      <div className="field-group">
        <label>Min ROCE (%)</label>
        <input type="number" value={config.min_roce} onChange={(e) => update("min_roce", Number(e.target.value))} />
      </div>
      <div className="checkbox-row">
        <input
          type="checkbox"
          id="positive_pat"
          checked={config.require_positive_pat}
          onChange={(e) => update("require_positive_pat", e.target.checked)}
        />
        <label htmlFor="positive_pat" style={{ margin: 0 }}>Require positive PAT</label>
      </div>

      <div className="section-title">Ranking</div>
      {config.rank_metrics.map((rm, idx) => (
        <div className="add-metric-row" key={idx}>
          <select value={rm.metric} onChange={(e) => updateRankMetric(idx, "metric", e.target.value)}>
            {METRIC_OPTIONS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <select value={rm.direction} onChange={(e) => updateRankMetric(idx, "direction", e.target.value)}>
            <option value="desc">High to Low</option>
            <option value="asc">Low to High</option>
          </select>
          {config.rank_metrics.length > 1 && (
            <button className="remove-btn" onClick={() => removeRankMetric(idx)}>x</button>
          )}
        </div>
      ))}
      <button className="add-btn" onClick={addRankMetric}>+ add another ranking metric</button>

      <button className="run-button" onClick={onRun} disabled={loading}>
        {loading ? "Running..." : "Run Backtest"}
      </button>
    </div>
  );
}
