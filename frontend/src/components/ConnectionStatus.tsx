import { memo } from 'react';
import type { ConnectionStatus as ConnectionStatusType } from '../types/dashboard';

interface ConnectionStatusProps {
  status: ConnectionStatusType;
  error: string | null;
  onReconnect: () => void;
}

export const ConnectionStatus = memo(function ConnectionStatus({ status, error, onReconnect }: ConnectionStatusProps) {
  const getStatusColor = (): string => {
    switch (status) {
      case 'connected':
        return 'green';
      case 'connecting':
        return 'orange';
      case 'disconnected':
      case 'error':
        return 'red';
    }
  };

  const getStatusText = (): string => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection Error';
    }
  };

  return (
    <div className="connection-status">
      <span className="status-indicator" style={{ backgroundColor: getStatusColor() }} />
      <span className="status-text">{getStatusText()}</span>
      {error && <span className="status-error">({error})</span>}
      {(status === 'disconnected' || status === 'error') && (
        <button className="reconnect-button" onClick={onReconnect}>
          Reconnect
        </button>
      )}
    </div>
  );
});
