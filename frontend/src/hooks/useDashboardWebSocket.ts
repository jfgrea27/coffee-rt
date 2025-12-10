import { useState, useEffect, useCallback, useRef } from 'react';
import type { DashboardData, ConnectionStatus } from '../types/dashboard';

interface UseDashboardWebSocketOptions {
  url?: string;
  reconnectInterval?: number;
}

interface UseDashboardWebSocketResult {
  data: DashboardData | null;
  status: ConnectionStatus;
  error: string | null;
  lastUpdated: number | null;
  reconnect: () => void;
}

export function useDashboardWebSocket(
  options: UseDashboardWebSocketOptions = {}
): UseDashboardWebSocketResult {
  const {
    url = `ws://${window.location.host}/ws/dashboard`,
    reconnectInterval = 5000,
  } = options;

  const [data, setData] = useState<DashboardData | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

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
        setData(dashboardData);
        setLastUpdated(Date.now());
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

  return { data, status, error, lastUpdated, reconnect };
}
