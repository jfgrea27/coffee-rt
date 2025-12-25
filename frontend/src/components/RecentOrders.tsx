import { memo } from "react";
import type { RecentOrder } from "../types/dashboard";

interface RecentOrdersProps {
  orders: RecentOrder[];
}

function ordersEqual(a: RecentOrder[], b: RecentOrder[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((order, index) => order.id === b[index].id);
}

export const RecentOrders = memo(
  function RecentOrders({ orders }: RecentOrdersProps) {
    const formatTimestamp = (timestamp: string): string => {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    };

    return (
      <div className="dashboard-card recent-orders">
        <h2>Recent Orders</h2>
        {orders.length === 0 ? (
          <p className="no-data">No recent orders</p>
        ) : (
          <div className="orders-container">
            <table className="orders-table">
              <thead>
                <tr>
                  <th>Drink</th>
                  <th>Store</th>
                  <th>Price</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>{order.drink}</td>
                    <td>{order.store}</td>
                    <td>${order.price.toFixed(2)}</td>
                    <td>{formatTimestamp(order.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  },
  (prevProps, nextProps) => ordersEqual(prevProps.orders, nextProps.orders)
);
