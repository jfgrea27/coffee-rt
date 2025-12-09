import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TopDrinks } from '../components/TopDrinks';

describe('TopDrinks', () => {
  it('renders no data message when drinks array is empty', () => {
    render(<TopDrinks drinks={[]} />);

    expect(screen.getByText('Top 5 Drinks (Last 30 Days)')).toBeInTheDocument();
    expect(screen.getByText('No drink data available')).toBeInTheDocument();
  });

  it('renders drinks list with rankings', () => {
    const drinks = ['latte', 'cappuccino', 'americano'];

    render(<TopDrinks drinks={drinks} />);

    expect(screen.getByText('Top 5 Drinks (Last 30 Days)')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('latte')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
    expect(screen.getByText('cappuccino')).toBeInTheDocument();
    expect(screen.getByText('#3')).toBeInTheDocument();
    expect(screen.getByText('americano')).toBeInTheDocument();
  });

  it('renders all 5 drinks when provided', () => {
    const drinks = ['latte', 'cappuccino', 'americano', 'espresso', 'mocha'];

    render(<TopDrinks drinks={drinks} />);

    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#5')).toBeInTheDocument();
    expect(screen.getByText('mocha')).toBeInTheDocument();
  });
});
