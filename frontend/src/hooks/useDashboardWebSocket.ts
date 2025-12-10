import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { DashboardData, ConnectionStatus, HourlyMetrics, RecentOrder } from '../types/dashboard';

interface UseDashboardWebSocketOptions {
  url?: string;
  reconnectInterval?: number;
}

interface UseDashboardWebSocketResult {
  data: DashboardData | null;
  status: ConnectionStatus;
  error: string | null;
  serverTimestamp: string | null;
  reconnect: () => void;
}

// Comparison helpers to avoid unnecessary state updates
function metricsEqual(a: HourlyMetrics | null, b: HourlyMetrics | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.hour === b.hour &&
    a.order_count === b.order_count &&
    a.revenue === b.revenue &&
    a.top_drinks.length === b.top_drinks.length &&
    a.top_drinks.every((drink, i) => drink === b.top_drinks[i])
  );
}

function drinksEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((drink, i) => drink === b[i]);
}

function ordersEqual(a: RecentOrder[], b: RecentOrder[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((order, i) => order.id === b[i].id);
}

export function useDashboardWebSocket(
  options: UseDashboardWebSocketOptions = {}
): UseDashboardWebSocketResult {
  const {
    url = `ws://${window.location.host}/ws/dashboard`,
    reconnectInterval = 5000,
  } = options;

  // Split state for granular updates - only re-render components whose data changed
  const [currentHour, setCurrentHour] = useState<HourlyMetrics | null>(null);
  const [top5Drinks, setTop5Drinks] = useState<string[]>([]);
  const [recentOrders, setRecentOrders] = useState<RecentOrder[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [serverTimestamp, setServerTimestamp] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Refs to track previous values for comparison (avoid closure stale data)
  const currentHourRef = useRef(currentHour);
  const top5DrinksRef = useRef(top5Drinks);
  const recentOrdersRef = useRef(recentOrders);

  // Keep refs in sync
  currentHourRef.current = currentHour;
  top5DrinksRef.current = top5Drinks;
  recentOrdersRef.current = recentOrders;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus('connecting');
    setError(null);

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const dashboardData: DashboardData = JSON.parse(event.data);

        // Always update server timestamp on every message
        setServerTimestamp(dashboardData.server_timestamp);

        // Only update other state for data that has actually changed
        if (!metricsEqual(currentHourRef.current, dashboardData.current_hour)) {
          setCurrentHour(dashboardData.current_hour);
        }

        if (!drinksEqual(top5DrinksRef.current, dashboardData.top5_drinks)) {
          setTop5Drinks(dashboardData.top5_drinks);
        }

        if (!ordersEqual(recentOrdersRef.current, dashboardData.recent_orders)) {
          setRecentOrders(dashboardData.recent_orders);
        }
      } catch {
        console.error('Failed to parse WebSocket message');
      }
    };

    ws.onerror = () => {
      setStatus('error');
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      setStatus('disconnected');
      wsRef.current = null;

      // Auto-reconnect
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, reconnectInterval);
    };
  }, [url, reconnectInterval]);

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Compose the data object - memoized to maintain reference stability
  const data = useMemo<DashboardData | null>(() => {
    if (!currentHour && top5Drinks.length === 0 && recentOrders.length === 0 && !serverTimestamp) {
      return null;
    }
    return {
      current_hour: currentHour,
      top5_drinks: top5Drinks,
      recent_orders: recentOrders,
      server_timestamp: serverTimestamp ?? '',
    };
  }, [currentHour, top5Drinks, recentOrders, serverTimestamp]);

  return { data, status, error, serverTimestamp, reconnect };
}
