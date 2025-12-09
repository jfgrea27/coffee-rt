import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConnectionStatus } from '../components/ConnectionStatus';

describe('ConnectionStatus', () => {
  it('renders connected status with green indicator', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus status="connected" error={null} onReconnect={onReconnect} />);

    expect(screen.getByText('Connected')).toBeInTheDocument();
    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toBeInTheDocument();
  });

  it('renders connecting status with indicator', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus status="connecting" error={null} onReconnect={onReconnect} />);

    expect(screen.getByText('Connecting...')).toBeInTheDocument();
    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toBeInTheDocument();
  });

  it('renders disconnected status with reconnect button', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus status="disconnected" error={null} onReconnect={onReconnect} />);

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
    expect(screen.getByText('Reconnect')).toBeInTheDocument();
    const indicator = document.querySelector('.status-indicator');
    expect(indicator).toBeInTheDocument();
  });

  it('renders error status with error message', () => {
    const onReconnect = vi.fn();
    render(
      <ConnectionStatus
        status="error"
        error="Connection failed"
        onReconnect={onReconnect}
      />
    );

    expect(screen.getByText('Connection Error')).toBeInTheDocument();
    expect(screen.getByText('(Connection failed)')).toBeInTheDocument();
  });

  it('calls onReconnect when reconnect button is clicked', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus status="disconnected" error={null} onReconnect={onReconnect} />);

    const button = screen.getByText('Reconnect');
    fireEvent.click(button);

    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it('does not show reconnect button when connected', () => {
    const onReconnect = vi.fn();
    render(<ConnectionStatus status="connected" error={null} onReconnect={onReconnect} />);

    expect(screen.queryByText('Reconnect')).not.toBeInTheDocument();
  });
});
