import { useEffect, useState } from 'react';
import { useDashboardWebSocket } from '../hooks/useDashboardWebSocket';
import { HourlyMetrics } from './HourlyMetrics';
import { TopDrinks } from './TopDrinks';
import { RecentOrders } from './RecentOrders';
import { ConnectionStatus } from './ConnectionStatus';

export function Dashboard() {
  const { data, status, error, lastUpdated, reconnect } = useDashboardWebSocket();
  const [isBlinking, setIsBlinking] = useState(false);

  useEffect(() => {
    if (lastUpdated) {
      setIsBlinking(true);
      const timer = setTimeout(() => setIsBlinking(false), 500);
      return () => clearTimeout(timer);
    }
  }, [lastUpdated]);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Cafe Dashboard</h1>
        <ConnectionStatus status={status} error={error} onReconnect={reconnect} />
      </header>

      <main className={`dashboard-content ${isBlinking ? 'blink' : ''}`}>
        <HourlyMetrics metrics={data?.current_hour ?? null} />
        <TopDrinks drinks={data?.top5_drinks ?? []} />
        <RecentOrders orders={data?.recent_orders ?? []} />
      </main>

      <footer className="dashboard-footer">
        <p>Data updates every 30 seconds via WebSocket</p>
      </footer>
    </div>
  );
}
