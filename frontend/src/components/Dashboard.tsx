import { useEffect, useState } from "react";
import { useDashboardWebSocket } from "../hooks/useDashboardWebSocket";
import { HourlyMetrics } from "./HourlyMetrics";
import { TopDrinks } from "./TopDrinks";
import { RecentOrders } from "./RecentOrders";
import { ConnectionStatus } from "./ConnectionStatus";
import { LastUpdated } from "./LastUpdated";
import { ThemeToggle } from "./ThemeToggle";

export function Dashboard() {
  const { data, status, error, serverTimestamp, reconnect } =
    useDashboardWebSocket();
  const [isBlinking, setIsBlinking] = useState(false);

  useEffect(() => {
    if (serverTimestamp) {
      setIsBlinking(true);
      const timer = setTimeout(() => setIsBlinking(false), 500);
      return () => clearTimeout(timer);
    }
  }, [serverTimestamp]);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Cafe Dashboard</h1>
        <div className="header-status">
          <LastUpdated timestamp={serverTimestamp} />
          <ConnectionStatus
            status={status}
            error={error}
            onReconnect={reconnect}
          />
          <ThemeToggle />
        </div>
      </header>

      <main className={`dashboard-content ${isBlinking ? "blink" : ""}`}>
        <HourlyMetrics metrics={data?.current_hour ?? null} />
        <TopDrinks drinks={data?.top5_drinks ?? []} />
        <RecentOrders orders={data?.recent_orders ?? []} />
      </main>

      <footer className="dashboard-footer">
        <p>Data updates via WebSocket</p>
      </footer>
    </div>
  );
}
