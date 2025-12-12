package com.coffeert.model;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;

class CoffeeOrderTest {

    private ObjectMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = new ObjectMapper().registerModule(new JavaTimeModule());
    }

    @Test
    void testDefaultConstructor() {
        CoffeeOrder order = new CoffeeOrder();
        assertNull(order.getMessageId());
        assertNull(order.getDrink());
        assertNull(order.getStore());
        assertNull(order.getPrice());
        assertNull(order.getTimestamp());
        assertNull(order.getVersion());
    }

    @Test
    void testParameterizedConstructor() {
        CoffeeOrder order = new CoffeeOrder(
            "msg-123",
            "latte",
            "downtown",
            new BigDecimal("4.50"),
            "2024-01-15T10:30:00Z",
            "v3"
        );

        assertEquals("msg-123", order.getMessageId());
        assertEquals("latte", order.getDrink());
        assertEquals("downtown", order.getStore());
        assertEquals(new BigDecimal("4.50"), order.getPrice());
        assertEquals("2024-01-15T10:30:00Z", order.getTimestamp());
        assertEquals("v3", order.getVersion());
    }

    @Test
    void testSettersAndGetters() {
        CoffeeOrder order = new CoffeeOrder();

        order.setMessageId("msg-456");
        order.setDrink("espresso");
        order.setStore("uptown");
        order.setPrice(new BigDecimal("3.00"));
        order.setTimestamp("2024-01-15T11:00:00Z");
        order.setVersion("v3");

        assertEquals("msg-456", order.getMessageId());
        assertEquals("espresso", order.getDrink());
        assertEquals("uptown", order.getStore());
        assertEquals(new BigDecimal("3.00"), order.getPrice());
        assertEquals("2024-01-15T11:00:00Z", order.getTimestamp());
        assertEquals("v3", order.getVersion());
    }

    @Test
    void testGetTimestampAsInstant_validTimestamp() {
        CoffeeOrder order = new CoffeeOrder();
        order.setTimestamp("2024-01-15T10:30:00Z");

        Instant instant = order.getTimestampAsInstant();

        assertEquals(Instant.parse("2024-01-15T10:30:00Z"), instant);
    }

    @Test
    void testGetTimestampAsInstant_nullTimestamp() {
        CoffeeOrder order = new CoffeeOrder();
        order.setTimestamp(null);

        Instant before = Instant.now();
        Instant instant = order.getTimestampAsInstant();
        Instant after = Instant.now();

        assertTrue(!instant.isBefore(before) && !instant.isAfter(after));
    }

    @Test
    void testGetTimestampAsInstant_invalidTimestamp() {
        CoffeeOrder order = new CoffeeOrder();
        order.setTimestamp("invalid-timestamp");

        Instant before = Instant.now();
        Instant instant = order.getTimestampAsInstant();
        Instant after = Instant.now();

        assertTrue(!instant.isBefore(before) && !instant.isAfter(after));
    }

    @Test
    void testJsonDeserialization() throws Exception {
        String json = "{" +
            "\"message_id\":\"msg-789\"," +
            "\"drink\":\"cappuccino\"," +
            "\"store\":\"midtown\"," +
            "\"price\":5.25," +
            "\"timestamp\":\"2024-01-15T12:00:00Z\"," +
            "\"version\":\"v3\"" +
        "}";

        CoffeeOrder order = mapper.readValue(json, CoffeeOrder.class);

        assertEquals("msg-789", order.getMessageId());
        assertEquals("cappuccino", order.getDrink());
        assertEquals("midtown", order.getStore());
        assertEquals(new BigDecimal("5.25"), order.getPrice());
        assertEquals("2024-01-15T12:00:00Z", order.getTimestamp());
        assertEquals("v3", order.getVersion());
    }

    @Test
    void testJsonDeserialization_unknownFieldsIgnored() throws Exception {
        String json = "{" +
            "\"message_id\":\"msg-789\"," +
            "\"drink\":\"latte\"," +
            "\"store\":\"downtown\"," +
            "\"price\":4.50," +
            "\"unknown_field\":\"should be ignored\"," +
            "\"version\":\"v3\"" +
        "}";

        CoffeeOrder order = mapper.readValue(json, CoffeeOrder.class);

        assertEquals("msg-789", order.getMessageId());
        assertEquals("latte", order.getDrink());
    }

    @Test
    void testJsonSerialization() throws Exception {
        CoffeeOrder order = new CoffeeOrder(
            "msg-101",
            "mocha",
            "airport",
            new BigDecimal("6.00"),
            "2024-01-15T14:00:00Z",
            "v3"
        );

        String json = mapper.writeValueAsString(order);

        assertTrue(json.contains("\"message_id\":\"msg-101\""));
        assertTrue(json.contains("\"drink\":\"mocha\""));
        assertTrue(json.contains("\"store\":\"airport\""));
        assertTrue(json.contains("\"version\":\"v3\""));
    }

    @Test
    void testToString() {
        CoffeeOrder order = new CoffeeOrder(
            "msg-102",
            "americano",
            "station",
            new BigDecimal("3.50"),
            "2024-01-15T15:00:00Z",
            "v3"
        );

        String str = order.toString();

        assertTrue(str.contains("msg-102"));
        assertTrue(str.contains("americano"));
        assertTrue(str.contains("station"));
        assertTrue(str.contains("3.50"));
        assertTrue(str.contains("v3"));
    }
}
