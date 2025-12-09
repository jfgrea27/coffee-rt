import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RecentOrders } from '../components/RecentOrders';
import type { RecentOrder } from '../types/dashboard';

describe('RecentOrders', () => {
  it('renders no data message when orders array is empty', () => {
    render(<RecentOrders orders={[]} />);

    expect(screen.getByText('Recent Orders')).toBeInTheDocument();
    expect(screen.getByText('No recent orders')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    const orders: RecentOrder[] = [
      {
        id: 1,
        drink: 'latte',
        store: 'downtown',
        price: 4.5,
        timestamp: '2024-01-15T14:30:00Z',
      },
    ];

    render(<RecentOrders orders={orders} />);

    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Drink')).toBeInTheDocument();
    expect(screen.getByText('Store')).toBeInTheDocument();
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
  });

  it('renders order data correctly', () => {
    const orders: RecentOrder[] = [
      {
        id: 42,
        drink: 'cappuccino',
        store: 'uptown',
        price: 5.25,
        timestamp: '2024-01-15T14:30:00Z',
      },
    ];

    render(<RecentOrders orders={orders} />);

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('cappuccino')).toBeInTheDocument();
    expect(screen.getByText('uptown')).toBeInTheDocument();
    expect(screen.getByText('$5.25')).toBeInTheDocument();
  });

  it('renders multiple orders', () => {
    const orders: RecentOrder[] = [
      {
        id: 1,
        drink: 'latte',
        store: 'downtown',
        price: 4.5,
        timestamp: '2024-01-15T14:30:00Z',
      },
      {
        id: 2,
        drink: 'americano',
        store: 'central',
        price: 3.75,
        timestamp: '2024-01-15T14:35:00Z',
      },
    ];

    render(<RecentOrders orders={orders} />);

    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('latte')).toBeInTheDocument();
    expect(screen.getByText('americano')).toBeInTheDocument();
  });
});
