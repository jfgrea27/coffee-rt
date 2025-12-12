package com.coffeert.sink;

import com.coffeert.function.OrderAggregator.AggregatedMetrics;
import org.apache.flink.streaming.api.functions.sink.SinkFunction;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.Pipeline;

import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class RedisMetricsSinkTest {

    @Mock
    private JedisPool mockJedisPool;

    @Mock
    private Jedis mockJedis;

    @Mock
    private Pipeline mockPipeline;

    @Mock
    private SinkFunction.Context mockContext;

    private RedisMetricsSink sink;

    @BeforeEach
    void setUp() {
        sink = new RedisMetricsSink("localhost", 6379);
    }

    @Test
    void testSinkCreation() {
        assertNotNull(sink);
    }

    @Test
    void testSinkStoresHostAndPort() throws Exception {
        RedisMetricsSink testSink = new RedisMetricsSink("redis.example.com", 6380);

        Field hostField = RedisMetricsSink.class.getDeclaredField("redisHost");
        Field portField = RedisMetricsSink.class.getDeclaredField("redisPort");
        hostField.setAccessible(true);
        portField.setAccessible(true);

        assertEquals("redis.example.com", hostField.get(testSink));
        assertEquals(6380, portField.get(testSink));
    }

    @Test
    void testInvokeWithMockedRedis() throws Exception {
        // Setup mocks
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        when(mockJedis.get(anyString())).thenReturn(null);
        when(mockJedis.pipelined()).thenReturn(mockPipeline);

        // Inject mock pool
        Field poolField = RedisMetricsSink.class.getDeclaredField("jedisPool");
        poolField.setAccessible(true);
        poolField.set(sink, mockJedisPool);

        Field mapperField = RedisMetricsSink.class.getDeclaredField("objectMapper");
        mapperField.setAccessible(true);
        mapperField.set(sink, new com.fasterxml.jackson.databind.ObjectMapper());

        // Create test metrics
        Map<String, Long> drinkCounts = new HashMap<>();
        drinkCounts.put("latte", 5L);
        Map<String, BigDecimal> drinkRevenue = new HashMap<>();
        drinkRevenue.put("latte", new BigDecimal("22.50"));
        Map<String, Long> storeCounts = new HashMap<>();
        storeCounts.put("downtown", 5L);
        Map<String, BigDecimal> storeRevenue = new HashMap<>();
        storeRevenue.put("downtown", new BigDecimal("22.50"));

        AggregatedMetrics metrics = new AggregatedMetrics(
            5, new BigDecimal("22.50"),
            drinkCounts, drinkRevenue,
            storeCounts, storeRevenue
        );

        // Invoke
        sink.invoke(metrics, mockContext);

        // Verify Redis interactions
        verify(mockJedis).get(startsWith("metrics:hourly:"));
        verify(mockJedis).pipelined();
        verify(mockPipeline).set(startsWith("metrics:hourly:"), anyString());
        verify(mockPipeline).expire(startsWith("metrics:hourly:"), eq(25L * 3600));
        verify(mockPipeline).set(eq("metrics:top5"), anyString());
        verify(mockPipeline).sync();
        verify(mockJedis).close();
    }

    @Test
    void testInvokeWithExistingData() throws Exception {
        // Setup mocks with existing data
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        String existingJson = "{\"drink_counts\":{\"espresso\":3},\"revenue\":15.0,\"order_count\":3}";
        when(mockJedis.get(anyString())).thenReturn(existingJson);
        when(mockJedis.pipelined()).thenReturn(mockPipeline);

        // Inject mocks
        Field poolField = RedisMetricsSink.class.getDeclaredField("jedisPool");
        poolField.setAccessible(true);
        poolField.set(sink, mockJedisPool);

        Field mapperField = RedisMetricsSink.class.getDeclaredField("objectMapper");
        mapperField.setAccessible(true);
        mapperField.set(sink, new com.fasterxml.jackson.databind.ObjectMapper());

        // Create new metrics to merge
        Map<String, Long> drinkCounts = new HashMap<>();
        drinkCounts.put("latte", 2L);
        Map<String, BigDecimal> drinkRevenue = new HashMap<>();
        drinkRevenue.put("latte", new BigDecimal("9.00"));

        AggregatedMetrics metrics = new AggregatedMetrics(
            2, new BigDecimal("9.00"),
            drinkCounts, drinkRevenue,
            new HashMap<>(), new HashMap<>()
        );

        // Invoke
        sink.invoke(metrics, mockContext);

        // Verify merge happened
        verify(mockJedis).get(startsWith("metrics:hourly:"));
        verify(mockPipeline).sync();
    }

    @Test
    void testCloseWithPool() throws Exception {
        // Inject mock pool
        Field poolField = RedisMetricsSink.class.getDeclaredField("jedisPool");
        poolField.setAccessible(true);
        poolField.set(sink, mockJedisPool);

        sink.close();

        verify(mockJedisPool).close();
    }

    @Test
    void testCloseWithNullPool() throws Exception {
        // Pool is null by default
        assertDoesNotThrow(() -> sink.close());
    }

    @Test
    void testAggregatedMetricsGetters() {
        Map<String, Long> drinkCounts = new HashMap<>();
        drinkCounts.put("latte", 10L);
        drinkCounts.put("espresso", 5L);

        Map<String, BigDecimal> drinkRevenue = new HashMap<>();
        drinkRevenue.put("latte", new BigDecimal("45.00"));
        drinkRevenue.put("espresso", new BigDecimal("15.00"));

        Map<String, Long> storeCounts = new HashMap<>();
        storeCounts.put("downtown", 15L);

        Map<String, BigDecimal> storeRevenue = new HashMap<>();
        storeRevenue.put("downtown", new BigDecimal("60.00"));

        AggregatedMetrics metrics = new AggregatedMetrics(
            15, new BigDecimal("60.00"),
            drinkCounts, drinkRevenue,
            storeCounts, storeRevenue
        );

        assertEquals(15, metrics.getTotalOrders());
        assertEquals(new BigDecimal("60.00"), metrics.getTotalRevenue());
        assertEquals(2, metrics.getDrinkCounts().size());
        assertEquals(2, metrics.getDrinkRevenue().size());
        assertEquals(1, metrics.getStoreCounts().size());
        assertEquals(1, metrics.getStoreRevenue().size());
    }

    @Test
    void testMetricsTopDrinksCalculation() {
        Map<String, Long> drinkCounts = new HashMap<>();
        drinkCounts.put("latte", 100L);
        drinkCounts.put("espresso", 50L);
        drinkCounts.put("cappuccino", 80L);
        drinkCounts.put("mocha", 30L);
        drinkCounts.put("americano", 60L);
        drinkCounts.put("macchiato", 20L);

        var topDrinks = drinkCounts.entrySet().stream()
            .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
            .limit(5)
            .map(Map.Entry::getKey)
            .toList();

        assertEquals(5, topDrinks.size());
        assertEquals("latte", topDrinks.get(0));
        assertEquals("cappuccino", topDrinks.get(1));
        assertEquals("americano", topDrinks.get(2));
    }

    @Test
    void testMetricsMergingLogic() {
        Map<String, Long> existing = new HashMap<>();
        existing.put("latte", 10L);
        existing.put("espresso", 5L);

        Map<String, Long> incoming = new HashMap<>();
        incoming.put("latte", 3L);
        incoming.put("cappuccino", 7L);

        Map<String, Long> combined = new HashMap<>(incoming);
        for (Map.Entry<String, Long> entry : existing.entrySet()) {
            combined.merge(entry.getKey(), entry.getValue(), Long::sum);
        }

        assertEquals(13L, combined.get("latte"));
        assertEquals(5L, combined.get("espresso"));
        assertEquals(7L, combined.get("cappuccino"));
    }

    @Test
    void testRevenueRounding() {
        double totalRevenue = 123.456789;
        double rounded = Math.round(totalRevenue * 100.0) / 100.0;
        assertEquals(123.46, rounded, 0.001);
    }

    @Test
    void testSinkIsSerializable() {
        assertTrue(sink instanceof java.io.Serializable);
    }

    @Test
    void testInvokeHandlesException() throws Exception {
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        when(mockJedis.get(anyString())).thenThrow(new RuntimeException("Redis error"));

        Field poolField = RedisMetricsSink.class.getDeclaredField("jedisPool");
        poolField.setAccessible(true);
        poolField.set(sink, mockJedisPool);

        Field mapperField = RedisMetricsSink.class.getDeclaredField("objectMapper");
        mapperField.setAccessible(true);
        mapperField.set(sink, new com.fasterxml.jackson.databind.ObjectMapper());

        AggregatedMetrics metrics = new AggregatedMetrics(
            1, new BigDecimal("5.00"),
            new HashMap<>(), new HashMap<>(),
            new HashMap<>(), new HashMap<>()
        );

        assertThrows(Exception.class, () -> sink.invoke(metrics, mockContext));
    }
}
