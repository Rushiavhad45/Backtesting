import React from "react";

export default function PortfolioLogTable({ logs, onExport }) {
  return (
    <div className="chart-card">
      <div className="section-header">
        <h3 style={{ margin: 0 }}>Portfolio Logs</h3>
        <button className="export-button" onClick={onExport}>Export CSV</button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Rebalance Date</th>
              <th>Symbol</th>
              <th>Name</th>
              <th>Weight</th>
              <th>Entry Price</th>
              <th>Exit Price</th>
              <th>Return</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((row, idx) => (
              <tr key={idx}>
                <td>{row.rebalance_date}</td>
                <td>{row.symbol}</td>
                <td>{row.name}</td>
                <td>{row.weight}%</td>
                <td>{row.entry_price}</td>
                <td>{row.exit_price}</td>
                <td className={row.return_pct >= 0 ? "return-positive" : "return-negative"}>
                  {row.return_pct}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
