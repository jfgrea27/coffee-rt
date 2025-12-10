interface LastUpdatedProps {
  timestamp: string | null;
}

export function LastUpdated({ timestamp }: LastUpdatedProps) {
  if (!timestamp) {
    return (
      <div className="last-updated">
        <span className="last-updated-label">Last updated:</span>
        <span className="last-updated-value">--</span>
      </div>
    );
  }

  const formatTimestamp = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  };

  return (
    <div className="last-updated">
      <span className="last-updated-label">Last updated:</span>
      <span className="last-updated-value">{formatTimestamp(timestamp)}</span>
    </div>
  );
}
