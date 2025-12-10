import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDashboardWebSocket } from '../hooks/useDashboardWebSocket';

// Track WebSocket instances
let mockWebSocketInstances: MockWebSocket[] = [];

class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  readyState: number = 0; // CONNECTING

  constructor(url: string) {
    this.url = url;
    mockWebSocketInstances.push(this);
    // Auto-trigger events after construction in microtask
    setTimeout(() => {
      // Allow test to set up handlers first
    }, 0);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3; // CLOSED
  });

  simulateOpen() {
    this.readyState = 1; // OPEN
    if (this.onopen) this.onopen();
  }

  simulateMessage(data: unknown) {
    if (this.onmessage) this.onmessage({ data: JSON.stringify(data) });
  }

  simulateError() {
    if (this.onerror) this.onerror();
  }

  simulateClose() {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose();
  }
}

// Add static constants
Object.defineProperty(MockWebSocket, 'CONNECTING', { value: 0 });
Object.defineProperty(MockWebSocket, 'OPEN', { value: 1 });
Object.defineProperty(MockWebSocket, 'CLOSING', { value: 2 });
Object.defineProperty(MockWebSocket, 'CLOSED', { value: 3 });

describe('useDashboardWebSocket', () => {
  beforeEach(() => {
    mockWebSocketInstances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('starts with connecting status', () => {
    const { result } = renderHook(() =>
      useDashboardWebSocket({ url: 'ws://test/ws/dashboard' })
    );

    expect(result.current.status).toBe('connecting');
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('creates a WebSocket connection', async () => {
    renderHook(() => useDashboardWebSocket({ url: 'ws://test/ws/dashboard' }));

    await vi.runAllTimersAsync();

    expect(mockWebSocketInstances.length).toBe(1);
    expect(mockWebSocketInstances[0].url).toBe('ws://test/ws/dashboard');
  });

  it('updates to connected status when WebSocket opens', async () => {
    const { result } = renderHook(() =>
      useDashboardWebSocket({ url: 'ws://test/ws/dashboard' })
    );

    await vi.runAllTimersAsync();

    const ws = mockWebSocketInstances[0];

    await act(async () => {
      ws.simulateOpen();
    });

    expect(result.current.status).toBe('connected');
  });

  it('updates data when receiving message', async () => {
    const { result } = renderHook(() =>
      useDashboardWebSocket({ url: 'ws://test/ws/dashboard' })
    );

    await vi.runAllTimersAsync();

    const ws = mockWebSocketInstances[0];
    const mockData = {
      current_hour: { hour: 14, top_drinks: ['latte'], revenue: 100, order_count: 20 },
      top5_drinks: ['latte', 'cappuccino'],
      recent_orders: [],
      server_timestamp: '2025-12-10T22:30:00+00:00',
    };

    await act(async () => {
      ws.simulateOpen();
    });

    await act(async () => {
      ws.simulateMessage(mockData);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.serverTimestamp).toBe('2025-12-10T22:30:00+00:00');
  });

  it('sets error status on WebSocket error', async () => {
    const { result } = renderHook(() =>
      useDashboardWebSocket({ url: 'ws://test/ws/dashboard' })
    );

    await vi.runAllTimersAsync();

    const ws = mockWebSocketInstances[0];

    await act(async () => {
      ws.simulateError();
    });

    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe('WebSocket connection error');
  });

  it('sets disconnected status on WebSocket close', async () => {
    const { result } = renderHook(() =>
      useDashboardWebSocket({ url: 'ws://test/ws/dashboard' })
    );

    await vi.runAllTimersAsync();

    const ws = mockWebSocketInstances[0];

    await act(async () => {
      ws.simulateOpen();
    });

    await act(async () => {
      ws.simulateClose();
    });

    expect(result.current.status).toBe('disconnected');
  });
});
