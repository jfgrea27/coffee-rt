package com.coffeert.function;

import com.coffeert.model.CoffeeOrder;
import org.apache.flink.api.common.functions.AggregateFunction;
import java.io.Serializable;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

/**
 * Aggregates coffee orders within a time window.
 * Accumulates counts and totals by drink and store.
 */
public class OrderAggregator
        implements AggregateFunction<CoffeeOrder, OrderAggregator.Accumulator,
        OrderAggregator.AggregatedMetrics> {

    @Override
    public Accumulator createAccumulator() {
        return new Accumulator();
    }

    @Override
    public Accumulator add(CoffeeOrder order, Accumulator acc) {
        acc.totalOrders++;
        acc.totalRevenue = acc.totalRevenue.add(order.getPrice() != null ? order.getPrice() : BigDecimal.ZERO);

        // Count by drink
        String drink = order.getDrink();
        if (drink != null) {
            acc.drinkCounts.merge(drink, 1L, Long::sum);
            BigDecimal drinkPrice = order.getPrice() != null ? order.getPrice() : BigDecimal.ZERO;
            acc.drinkRevenue.merge(drink, drinkPrice, BigDecimal::add);
        }

        // Count by store
        String store = order.getStore();
        if (store != null) {
            acc.storeCounts.merge(store, 1L, Long::sum);
            BigDecimal storePrice = order.getPrice() != null ? order.getPrice() : BigDecimal.ZERO;
            acc.storeRevenue.merge(store, storePrice, BigDecimal::add);
        }

        return acc;
    }

    @Override
    public AggregatedMetrics getResult(Accumulator acc) {
        return new AggregatedMetrics(
                acc.totalOrders,
                acc.totalRevenue,
                new HashMap<>(acc.drinkCounts),
                new HashMap<>(acc.drinkRevenue),
                new HashMap<>(acc.storeCounts),
                new HashMap<>(acc.storeRevenue)
        );
    }

    @Override
    public Accumulator merge(Accumulator a, Accumulator b) {
        a.totalOrders += b.totalOrders;
        a.totalRevenue = a.totalRevenue.add(b.totalRevenue);

        b.drinkCounts.forEach((k, v) -> a.drinkCounts.merge(k, v, Long::sum));
        b.drinkRevenue.forEach((k, v) -> a.drinkRevenue.merge(k, v, BigDecimal::add));
        b.storeCounts.forEach((k, v) -> a.storeCounts.merge(k, v, Long::sum));
        b.storeRevenue.forEach((k, v) -> a.storeRevenue.merge(k, v, BigDecimal::add));

        return a;
    }

    /**
     * Mutable accumulator for aggregation state.
     */
    public static class Accumulator implements Serializable {
        private static final long serialVersionUID = 1L;

        long totalOrders = 0;
        BigDecimal totalRevenue = BigDecimal.ZERO;
        Map<String, Long> drinkCounts = new HashMap<>();
        Map<String, BigDecimal> drinkRevenue = new HashMap<>();
        Map<String, Long> storeCounts = new HashMap<>();
        Map<String, BigDecimal> storeRevenue = new HashMap<>();
    }

    /**
     * Immutable result of aggregation.
     */
    public static class AggregatedMetrics implements Serializable {
        private static final long serialVersionUID = 1L;

        private final long totalOrders;
        private final BigDecimal totalRevenue;
        private final Map<String, Long> drinkCounts;
        private final Map<String, BigDecimal> drinkRevenue;
        private final Map<String, Long> storeCounts;
        private final Map<String, BigDecimal> storeRevenue;

        public AggregatedMetrics(long totalOrders, BigDecimal totalRevenue,
                                  Map<String, Long> drinkCounts, Map<String, BigDecimal> drinkRevenue,
                                  Map<String, Long> storeCounts, Map<String, BigDecimal> storeRevenue) {
            this.totalOrders = totalOrders;
            this.totalRevenue = totalRevenue;
            this.drinkCounts = drinkCounts;
            this.drinkRevenue = drinkRevenue;
            this.storeCounts = storeCounts;
            this.storeRevenue = storeRevenue;
        }

        public long getTotalOrders() {
            return totalOrders;
        }

        public BigDecimal getTotalRevenue() {
            return totalRevenue;
        }

        public Map<String, Long> getDrinkCounts() {
            return drinkCounts;
        }

        public Map<String, BigDecimal> getDrinkRevenue() {
            return drinkRevenue;
        }

        public Map<String, Long> getStoreCounts() {
            return storeCounts;
        }

        public Map<String, BigDecimal> getStoreRevenue() {
            return storeRevenue;
        }

        @Override
        public String toString() {
            return "AggregatedMetrics{" +
                    "totalOrders=" + totalOrders +
                    ", totalRevenue=" + totalRevenue +
                    ", drinkCounts=" + drinkCounts +
                    ", storeCounts=" + storeCounts +
                    '}';
        }
    }
}
