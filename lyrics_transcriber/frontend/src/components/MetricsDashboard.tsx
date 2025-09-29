import React from "react";

type Metrics = {
  timeRange: string;
  totalSessions: number;
  averageAccuracy: number;
  errorReduction: number;
  averageProcessingTime: number;
  modelPerformance: { counts: Record<string, number>; avgLatencyMs: Record<string, number>; fallbacks: number };
  costSummary: Record<string, number>;
  userSatisfaction: number;
};

type Props = { metrics: Metrics };

export const MetricsDashboard: React.FC<Props> = ({ metrics }) => {
  const modelIds = Object.keys(metrics.modelPerformance.counts || {});
  return (
    <div>
      <h3>Agentic Metrics</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        <div><b>Total Sessions</b><div>{metrics.totalSessions}</div></div>
        <div><b>Avg Proc Time (ms)</b><div>{metrics.averageProcessingTime}</div></div>
        <div><b>Fallbacks</b><div>{metrics.modelPerformance.fallbacks}</div></div>
      </div>
      <h4 style={{ marginTop: 16 }}>Per-Model</h4>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Model</th>
            <th style={{ textAlign: "right" }}>Count</th>
            <th style={{ textAlign: "right" }}>Avg Latency (ms)</th>
          </tr>
        </thead>
        <tbody>
          {modelIds.map((id) => (
            <tr key={id}>
              <td>{id}</td>
              <td style={{ textAlign: "right" }}>{metrics.modelPerformance.counts[id] || 0}</td>
              <td style={{ textAlign: "right" }}>{metrics.modelPerformance.avgLatencyMs[id] || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default MetricsDashboard;


