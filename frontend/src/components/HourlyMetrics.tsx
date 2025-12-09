import type { HourlyMetrics as HourlyMetricsType } from '../types/dashboard';

interface HourlyMetricsProps {
  metrics: HourlyMetricsType | null;
}

export function HourlyMetrics({ metrics }: HourlyMetricsProps) {
  if (!metrics) {
    return (
      <div className="dashboard-card hourly-metrics">
        <h2>Current Hour Metrics</h2>
        <p className="no-data">No metrics available for the current hour</p>
      </div>
    );
  }

  return (
    <div className="dashboard-card hourly-metrics">
      <h2>Current Hour Metrics</h2>
      <div className="metrics-grid">
        <div className="metric">
          <span className="metric-label">Hour</span>
          <span className="metric-value">{metrics.hour}:00</span>
        </div>
        <div className="metric">
          <span className="metric-label">Orders</span>
          <span className="metric-value">{metrics.order_count}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Revenue</span>
          <span className="metric-value">${metrics.revenue.toFixed(2)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Top Drinks</span>
          <span className="metric-value">{metrics.top_drinks.join(', ') || 'N/A'}</span>
        </div>
      </div>
    </div>
  );
}
