import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { Dashboard } from '../components/Dashboard';
import * as useDashboardWebSocketModule from '../hooks/useDashboardWebSocket';

vi.mock('../hooks/useDashboardWebSocket');

describe('Dashboard', () => {
  const mockReconnect = vi.fn();

  const localStorageMock = {
    getItem: vi.fn().mockReturnValue(null),
    setItem: vi.fn(),
    clear: vi.fn(),
  };

  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard header with title', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connecting',
      error: null,
      serverTimestamp: null,
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Cafe Dashboard')).toBeInTheDocument();
  });

  it('renders footer', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connecting',
      error: null,
      serverTimestamp: null,
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Data updates via WebSocket')).toBeInTheDocument();
  });

  it('renders ConnectionStatus component', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connected',
      error: null,
      serverTimestamp: null,
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('renders ThemeToggle component', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connecting',
      error: null,
      serverTimestamp: null,
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    const themeButton = screen.getByRole('button', { name: /switch to/i });
    expect(themeButton).toBeInTheDocument();
  });

  it('renders HourlyMetrics with null data', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connected',
      error: null,
      serverTimestamp: null,
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Current Hour Metrics')).toBeInTheDocument();
    expect(screen.getByText('No metrics available for the current hour')).toBeInTheDocument();
  });

  it('renders HourlyMetrics with data', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: {
        current_hour: {
          hour: 14,
          top_drinks: ['latte', 'cappuccino'],
          revenue: 125.5,
          order_count: 25,
        },
        top5_drinks: [],
        recent_orders: [],
        server_timestamp: '2025-12-11T14:00:00Z',
      },
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:00:00Z',
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('14:00')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('$125.50')).toBeInTheDocument();
  });

  it('renders TopDrinks with data', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: {
        current_hour: null,
        top5_drinks: ['latte', 'cappuccino', 'americano'],
        recent_orders: [],
        server_timestamp: '2025-12-11T14:00:00Z',
      },
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:00:00Z',
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Top 5 Drinks (Last 30 Days)')).toBeInTheDocument();
    expect(screen.getByText('latte')).toBeInTheDocument();
    expect(screen.getByText('cappuccino')).toBeInTheDocument();
    expect(screen.getByText('americano')).toBeInTheDocument();
  });

  it('renders RecentOrders with data', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: {
        current_hour: null,
        top5_drinks: [],
        recent_orders: [
          {
            id: 1,
            drink: 'latte',
            store: 'downtown',
            price: 5.5,
            timestamp: '2025-12-11T14:30:00Z',
          },
        ],
        server_timestamp: '2025-12-11T14:00:00Z',
      },
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:00:00Z',
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Recent Orders')).toBeInTheDocument();
    expect(screen.getByText('latte')).toBeInTheDocument();
    expect(screen.getByText('downtown')).toBeInTheDocument();
  });

  it('renders LastUpdated with timestamp', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:30:00Z',
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText(/Last updated:/i)).toBeInTheDocument();
  });

  it('shows error status when error occurs', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'error',
      error: 'Connection failed',
      serverTimestamp: null,
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Connection Error')).toBeInTheDocument();
    expect(screen.getByText('(Connection failed)')).toBeInTheDocument();
  });

  it('applies blink class when serverTimestamp changes', async () => {
    vi.useFakeTimers();

    const { rerender } = render(<Dashboard />);

    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: null,
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:30:00Z',
      reconnect: mockReconnect,
    });

    rerender(<Dashboard />);

    const content = document.querySelector('.dashboard-content');
    expect(content).toHaveClass('blink');

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(content).not.toHaveClass('blink');

    vi.useRealTimers();
  });

  it('renders empty TopDrinks when no drinks', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: {
        current_hour: null,
        top5_drinks: [],
        recent_orders: [],
        server_timestamp: '2025-12-11T14:00:00Z',
      },
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:00:00Z',
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Top 5 Drinks (Last 30 Days)')).toBeInTheDocument();
    expect(screen.getByText('No drink data available')).toBeInTheDocument();
  });

  it('renders empty RecentOrders when no orders', () => {
    vi.mocked(useDashboardWebSocketModule.useDashboardWebSocket).mockReturnValue({
      data: {
        current_hour: null,
        top5_drinks: [],
        recent_orders: [],
        server_timestamp: '2025-12-11T14:00:00Z',
      },
      status: 'connected',
      error: null,
      serverTimestamp: '2025-12-11T14:00:00Z',
      reconnect: mockReconnect,
    });

    render(<Dashboard />);

    expect(screen.getByText('Recent Orders')).toBeInTheDocument();
    expect(screen.getByText('No recent orders')).toBeInTheDocument();
  });
});
