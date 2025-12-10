import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LastUpdated } from '../components/LastUpdated';

describe('LastUpdated', () => {
  it('renders placeholder when timestamp is null', () => {
    render(<LastUpdated timestamp={null} />);

    expect(screen.getByText('Last updated:')).toBeInTheDocument();
    expect(screen.getByText('--')).toBeInTheDocument();
  });

  it('renders formatted UTC timestamp', () => {
    render(<LastUpdated timestamp="2025-12-10T22:30:45.123456+00:00" />);

    expect(screen.getByText('Last updated:')).toBeInTheDocument();
    expect(screen.getByText('2025-12-10 22:30:45 UTC')).toBeInTheDocument();
  });

  it('formats different timestamps correctly', () => {
    render(<LastUpdated timestamp="2025-01-15T08:05:30+00:00" />);

    expect(screen.getByText('2025-01-15 08:05:30 UTC')).toBeInTheDocument();
  });
});
