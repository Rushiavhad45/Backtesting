import React from "react";

export default function WinnersLosers({ winners, losers }) {
  return (
    <div className="two-col">
      <div className="chart-card">
        <h3>Top Winners</h3>
        <table>
          <thead>
            <tr><th>Symbol</th><th>Name</th><th>Avg Return</th></tr>
          </thead>
          <tbody>
            {winners.map((w) => (
              <tr key={w.symbol}>
                <td>{w.symbol}</td>
                <td>{w.name}</td>
                <td className="return-positive">{w.avg_return_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="chart-card">
        <h3>Top Losers</h3>
        <table>
          <thead>
            <tr><th>Symbol</th><th>Name</th><th>Avg Return</th></tr>
          </thead>
          <tbody>
            {losers.map((l) => (
              <tr key={l.symbol}>
                <td>{l.symbol}</td>
                <td>{l.name}</td>
                <td className="return-negative">{l.avg_return_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
