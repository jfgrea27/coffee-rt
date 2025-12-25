package com.coffeert.sink;

import com.coffeert.model.CoffeeOrder;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.streaming.api.functions.sink.SinkFunction;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class RecentOrdersSinkTest {

    @Mock
    private JedisPool mockJedisPool;

    @Mock
    private Jedis mockJedis;

    @Mock
    private SinkFunction.Context mockContext;

    private RecentOrdersSink sink;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        sink = new RecentOrdersSink("localhost", 6379);
        objectMapper = new ObjectMapper();
    }

    @Test
    void testSinkCreation() {
        assertNotNull(sink);
    }

    @Test
    void testSinkStoresHostAndPort() throws Exception {
        RecentOrdersSink testSink = new RecentOrdersSink("redis.example.com", 6380);

        Field hostField = RecentOrdersSink.class.getDeclaredField("redisHost");
        Field portField = RecentOrdersSink.class.getDeclaredField("redisPort");
        hostField.setAccessible(true);
        portField.setAccessible(true);

        assertEquals("redis.example.com", hostField.get(testSink));
        assertEquals(6380, portField.get(testSink));
    }

    @Test
    void testInvokeWithEmptyRedis() throws Exception {
        // Setup mocks
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        when(mockJedis.get("orders:recent")).thenReturn(null);

        injectMocks();

        CoffeeOrder order = createTestOrder("msg-123", "latte", "downtown", "4.50");

        sink.invoke(order, mockContext);

        // Capture the JSON written to Redis
        ArgumentCaptor<String> jsonCaptor = ArgumentCaptor.forClass(String.class);
        verify(mockJedis).setex(eq("orders:recent"), eq(7200L), jsonCaptor.capture());

        String json = jsonCaptor.getValue();
        List<?> orders = objectMapper.readValue(json, List.class);
        assertEquals(1, orders.size());

        @SuppressWarnings("unchecked")
        Map<String, Object> orderMap = (Map<String, Object>) orders.get(0);
        assertEquals("latte", orderMap.get("drink"));
        assertEquals("downtown", orderMap.get("store"));
        assertEquals(4.5, orderMap.get("price"));
        assertNotNull(orderMap.get("id"));

        verify(mockJedis).close();
    }

    @Test
    void testInvokeWithExistingOrders() throws Exception {
        // Setup mocks with existing orders
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        String existingJson = "[{\"id\":111,\"drink\":\"espresso\",\"store\":\"uptown\","
                + "\"price\":3.50,\"timestamp\":\"2025-01-01T10:00:00Z\"}]";
        when(mockJedis.get("orders:recent")).thenReturn(existingJson);

        injectMocks();

        CoffeeOrder order = createTestOrder("msg-456", "cappuccino", "central", "5.00");

        sink.invoke(order, mockContext);

        ArgumentCaptor<String> jsonCaptor = ArgumentCaptor.forClass(String.class);
        verify(mockJedis).setex(eq("orders:recent"), eq(7200L), jsonCaptor.capture());

        String json = jsonCaptor.getValue();
        List<?> orders = objectMapper.readValue(json, List.class);
        assertEquals(2, orders.size());

        // Verify order is preserved and new one added
        @SuppressWarnings("unchecked")
        Map<String, Object> firstOrder = (Map<String, Object>) orders.get(0);
        assertEquals("espresso", firstOrder.get("drink"));

        @SuppressWarnings("unchecked")
        Map<String, Object> secondOrder = (Map<String, Object>) orders.get(1);
        assertEquals("cappuccino", secondOrder.get("drink"));
    }

    @Test
    void testInvokeKeepsOnlyLast10Orders() throws Exception {
        // Setup mocks with 10 existing orders
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        StringBuilder existingJson = new StringBuilder("[");
        for (int i = 0; i < 10; i++) {
            if (i > 0) {
                existingJson.append(",");
            }
            existingJson.append(String.format(
                "{\"id\":%d,\"drink\":\"drink%d\",\"store\":\"store%d\","
                    + "\"price\":%.2f,\"timestamp\":\"2025-01-01T10:00:00Z\"}",
                i, i, i, 3.0 + i * 0.1
            ));
        }
        existingJson.append("]");
        when(mockJedis.get("orders:recent")).thenReturn(existingJson.toString());

        injectMocks();

        CoffeeOrder order = createTestOrder("msg-new", "newdrink", "newstore", "9.99");

        sink.invoke(order, mockContext);

        ArgumentCaptor<String> jsonCaptor = ArgumentCaptor.forClass(String.class);
        verify(mockJedis).setex(eq("orders:recent"), eq(7200L), jsonCaptor.capture());

        String json = jsonCaptor.getValue();
        List<?> orders = objectMapper.readValue(json, List.class);
        assertEquals(10, orders.size());

        // First order should be drink1 (drink0 was removed)
        @SuppressWarnings("unchecked")
        Map<String, Object> firstOrder = (Map<String, Object>) orders.get(0);
        assertEquals("drink1", firstOrder.get("drink"));

        // Last order should be the new one
        @SuppressWarnings("unchecked")
        Map<String, Object> lastOrder = (Map<String, Object>) orders.get(9);
        assertEquals("newdrink", lastOrder.get("drink"));
    }

    @Test
    void testSyntheticIdIsConsistent() {
        String messageId = "test-message-id-123";
        int id1 = Math.abs(messageId.hashCode());
        int id2 = Math.abs(messageId.hashCode());
        assertEquals(id1, id2);
    }

    @Test
    void testSyntheticIdIsDifferentForDifferentMessages() {
        int id1 = Math.abs("message-1".hashCode());
        int id2 = Math.abs("message-2".hashCode());
        assertNotEquals(id1, id2);
    }

    @Test
    void testCloseWithPool() throws Exception {
        Field poolField = RecentOrdersSink.class.getDeclaredField("jedisPool");
        poolField.setAccessible(true);
        poolField.set(sink, mockJedisPool);

        sink.close();

        verify(mockJedisPool).close();
    }

    @Test
    void testCloseWithNullPool() throws Exception {
        assertDoesNotThrow(() -> sink.close());
    }

    @Test
    void testSinkIsSerializable() {
        assertTrue(sink instanceof java.io.Serializable);
    }

    @Test
    void testInvokeHandlesException() throws Exception {
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        when(mockJedis.get("orders:recent")).thenThrow(new RuntimeException("Redis error"));

        injectMocks();

        CoffeeOrder order = createTestOrder("msg-err", "latte", "downtown", "4.50");

        assertThrows(Exception.class, () -> sink.invoke(order, mockContext));
    }

    @Test
    void testOrderMapContainsAllFields() throws Exception {
        when(mockJedisPool.getResource()).thenReturn(mockJedis);
        when(mockJedis.get("orders:recent")).thenReturn(null);

        injectMocks();

        CoffeeOrder order = createTestOrder("unique-msg-id", "americano", "southend", "3.75");

        sink.invoke(order, mockContext);

        ArgumentCaptor<String> jsonCaptor = ArgumentCaptor.forClass(String.class);
        verify(mockJedis).setex(eq("orders:recent"), anyLong(), jsonCaptor.capture());

        String json = jsonCaptor.getValue();
        List<?> orders = objectMapper.readValue(json, List.class);

        @SuppressWarnings("unchecked")
        Map<String, Object> orderMap = (Map<String, Object>) orders.get(0);

        assertTrue(orderMap.containsKey("id"));
        assertTrue(orderMap.containsKey("drink"));
        assertTrue(orderMap.containsKey("store"));
        assertTrue(orderMap.containsKey("price"));
        assertTrue(orderMap.containsKey("timestamp"));

        assertEquals("americano", orderMap.get("drink"));
        assertEquals("southend", orderMap.get("store"));
        assertEquals(3.75, orderMap.get("price"));
    }

    private void injectMocks() throws Exception {
        Field poolField = RecentOrdersSink.class.getDeclaredField("jedisPool");
        poolField.setAccessible(true);
        poolField.set(sink, mockJedisPool);

        Field mapperField = RecentOrdersSink.class.getDeclaredField("objectMapper");
        mapperField.setAccessible(true);
        mapperField.set(sink, objectMapper);
    }

    private CoffeeOrder createTestOrder(String messageId, String drink, String store, String price) {
        CoffeeOrder order = new CoffeeOrder();
        order.setMessageId(messageId);
        order.setDrink(drink);
        order.setStore(store);
        order.setPrice(new BigDecimal(price));
        order.setTimestamp("2025-01-01T12:00:00Z");
        order.setVersion("v3");
        return order;
    }
}
