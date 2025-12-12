package com.coffeert.function;

import com.coffeert.function.OrderAggregator.Accumulator;
import com.coffeert.function.OrderAggregator.AggregatedMetrics;
import com.coffeert.model.CoffeeOrder;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;

class OrderAggregatorTest {

    private OrderAggregator aggregator;

    @BeforeEach
    void setUp() {
        aggregator = new OrderAggregator();
    }

    @Test
    void testCreateAccumulator() {
        Accumulator acc = aggregator.createAccumulator();

        assertNotNull(acc);
        assertEquals(0, acc.totalOrders);
        assertEquals(BigDecimal.ZERO, acc.totalRevenue);
        assertTrue(acc.drinkCounts.isEmpty());
        assertTrue(acc.drinkRevenue.isEmpty());
        assertTrue(acc.storeCounts.isEmpty());
        assertTrue(acc.storeRevenue.isEmpty());
    }

    @Test
    void testAddSingleOrder() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order = new CoffeeOrder(
            "msg-1", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );

        Accumulator result = aggregator.add(order, acc);

        assertEquals(1, result.totalOrders);
        assertEquals(new BigDecimal("4.50"), result.totalRevenue);
        assertEquals(1L, result.drinkCounts.get("latte"));
        assertEquals(new BigDecimal("4.50"), result.drinkRevenue.get("latte"));
        assertEquals(1L, result.storeCounts.get("downtown"));
        assertEquals(new BigDecimal("4.50"), result.storeRevenue.get("downtown"));
    }

    @Test
    void testAddMultipleOrders() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order1 = new CoffeeOrder(
            "msg-1", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );
        CoffeeOrder order2 = new CoffeeOrder(
            "msg-2", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:01:00Z", "v3"
        );
        CoffeeOrder order3 = new CoffeeOrder(
            "msg-3", "espresso", "uptown", new BigDecimal("3.00"), "2024-01-15T10:02:00Z", "v3"
        );

        acc = aggregator.add(order1, acc);
        acc = aggregator.add(order2, acc);
        acc = aggregator.add(order3, acc);

        assertEquals(3, acc.totalOrders);
        assertEquals(new BigDecimal("12.00"), acc.totalRevenue);
        assertEquals(2L, acc.drinkCounts.get("latte"));
        assertEquals(1L, acc.drinkCounts.get("espresso"));
        assertEquals(2L, acc.storeCounts.get("downtown"));
        assertEquals(1L, acc.storeCounts.get("uptown"));
    }

    @Test
    void testAddOrderWithNullPrice() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order = new CoffeeOrder(
            "msg-1", "latte", "downtown", null, "2024-01-15T10:00:00Z", "v3"
        );

        Accumulator result = aggregator.add(order, acc);

        assertEquals(1, result.totalOrders);
        assertEquals(BigDecimal.ZERO, result.totalRevenue);
        assertEquals(1L, result.drinkCounts.get("latte"));
        assertEquals(BigDecimal.ZERO, result.drinkRevenue.get("latte"));
    }

    @Test
    void testAddOrderWithNullDrink() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order = new CoffeeOrder(
            "msg-1", null, "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );

        Accumulator result = aggregator.add(order, acc);

        assertEquals(1, result.totalOrders);
        assertEquals(new BigDecimal("4.50"), result.totalRevenue);
        assertTrue(result.drinkCounts.isEmpty());
        assertEquals(1L, result.storeCounts.get("downtown"));
    }

    @Test
    void testAddOrderWithNullStore() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order = new CoffeeOrder(
            "msg-1", "latte", null, new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );

        Accumulator result = aggregator.add(order, acc);

        assertEquals(1, result.totalOrders);
        assertEquals(new BigDecimal("4.50"), result.totalRevenue);
        assertEquals(1L, result.drinkCounts.get("latte"));
        assertTrue(result.storeCounts.isEmpty());
    }

    @Test
    void testGetResult() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order1 = new CoffeeOrder(
            "msg-1", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );
        CoffeeOrder order2 = new CoffeeOrder(
            "msg-2", "espresso", "uptown", new BigDecimal("3.00"), "2024-01-15T10:01:00Z", "v3"
        );

        acc = aggregator.add(order1, acc);
        acc = aggregator.add(order2, acc);

        AggregatedMetrics metrics = aggregator.getResult(acc);

        assertEquals(2, metrics.getTotalOrders());
        assertEquals(new BigDecimal("7.50"), metrics.getTotalRevenue());
        assertEquals(1L, metrics.getDrinkCounts().get("latte"));
        assertEquals(1L, metrics.getDrinkCounts().get("espresso"));
        assertEquals(new BigDecimal("4.50"), metrics.getDrinkRevenue().get("latte"));
        assertEquals(new BigDecimal("3.00"), metrics.getDrinkRevenue().get("espresso"));
    }

    @Test
    void testMergeAccumulators() {
        Accumulator acc1 = aggregator.createAccumulator();
        Accumulator acc2 = aggregator.createAccumulator();

        CoffeeOrder order1 = new CoffeeOrder(
            "msg-1", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );
        CoffeeOrder order2 = new CoffeeOrder(
            "msg-2", "latte", "uptown", new BigDecimal("5.00"), "2024-01-15T10:01:00Z", "v3"
        );
        CoffeeOrder order3 = new CoffeeOrder(
            "msg-3", "espresso", "downtown", new BigDecimal("3.00"), "2024-01-15T10:02:00Z", "v3"
        );

        acc1 = aggregator.add(order1, acc1);
        acc2 = aggregator.add(order2, acc2);
        acc2 = aggregator.add(order3, acc2);

        Accumulator merged = aggregator.merge(acc1, acc2);

        assertEquals(3, merged.totalOrders);
        assertEquals(new BigDecimal("12.50"), merged.totalRevenue);
        assertEquals(2L, merged.drinkCounts.get("latte"));
        assertEquals(1L, merged.drinkCounts.get("espresso"));
        assertEquals(2L, merged.storeCounts.get("downtown"));
        assertEquals(1L, merged.storeCounts.get("uptown"));
    }

    @Test
    void testAggregatedMetricsToString() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order = new CoffeeOrder(
            "msg-1", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );
        acc = aggregator.add(order, acc);

        AggregatedMetrics metrics = aggregator.getResult(acc);
        String str = metrics.toString();

        assertTrue(str.contains("totalOrders=1"));
        assertTrue(str.contains("totalRevenue=4.50"));
        assertTrue(str.contains("latte"));
        assertTrue(str.contains("downtown"));
    }

    @Test
    void testAggregatedMetricsImmutability() {
        Accumulator acc = aggregator.createAccumulator();
        CoffeeOrder order = new CoffeeOrder(
            "msg-1", "latte", "downtown", new BigDecimal("4.50"), "2024-01-15T10:00:00Z", "v3"
        );
        acc = aggregator.add(order, acc);

        AggregatedMetrics metrics = aggregator.getResult(acc);

        // Verify that modifying the accumulator doesn't affect the result
        acc.totalOrders = 999;
        assertEquals(1, metrics.getTotalOrders());
    }
}
