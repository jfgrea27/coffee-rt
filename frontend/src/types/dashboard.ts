export interface HourlyMetrics {
  hour: number;
  top_drinks: string[];
  revenue: number;
  order_count: number;
}

export interface RecentOrder {
  id: number;
  drink: string;
  store: string;
  price: number;
  timestamp: string;
}

export interface DashboardData {
  current_hour: HourlyMetrics | null;
  top5_drinks: string[];
  recent_orders: RecentOrder[];
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
