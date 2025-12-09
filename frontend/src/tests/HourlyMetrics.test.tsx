import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HourlyMetrics } from '../components/HourlyMetrics';
import type { HourlyMetrics as HourlyMetricsType } from '../types/dashboard';

describe('HourlyMetrics', () => {
  it('renders no data message when metrics is null', () => {
    render(<HourlyMetrics metrics={null} />);

    expect(screen.getByText('Current Hour Metrics')).toBeInTheDocument();
    expect(screen.getByText('No metrics available for the current hour')).toBeInTheDocument();
  });

  it('renders metrics when data is provided', () => {
    const metrics: HourlyMetricsType = {
      hour: 14,
      top_drinks: ['latte', 'cappuccino'],
      revenue: 125.5,
      order_count: 25,
    };

    render(<HourlyMetrics metrics={metrics} />);

    expect(screen.getByText('Current Hour Metrics')).toBeInTheDocument();
    expect(screen.getByText('14:00')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('$125.50')).toBeInTheDocument();
    expect(screen.getByText('latte, cappuccino')).toBeInTheDocument();
  });

  it('renders N/A when top_drinks is empty', () => {
    const metrics: HourlyMetricsType = {
      hour: 10,
      top_drinks: [],
      revenue: 0,
      order_count: 0,
    };

    render(<HourlyMetrics metrics={metrics} />);

    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});
