interface TopDrinksProps {
  drinks: string[];
}

export function TopDrinks({ drinks }: TopDrinksProps) {
  return (
    <div className="dashboard-card top-drinks">
      <h2>Top 5 Drinks (Last 30 Days)</h2>
      {drinks.length === 0 ? (
        <p className="no-data">No drink data available</p>
      ) : (
        <ol className="drinks-list">
          {drinks.map((drink, index) => (
            <li key={`${drink}-${index}`} className="drink-item">
              <span className="drink-rank">#{index + 1}</span>
              <span className="drink-name">{drink}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
