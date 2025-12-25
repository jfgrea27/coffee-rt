package com.coffeert.sink;

import com.coffeert.model.CoffeeOrder;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.util.*;

/**
 * Flink sink that writes recent orders to Redis.
 * Maintains a rolling list of the last 10 orders in orders:recent.
 */
public class RecentOrdersSink extends RichSinkFunction<CoffeeOrder> {
    private static final Logger LOG = LoggerFactory.getLogger(RecentOrdersSink.class);
    private static final long serialVersionUID = 1L;
    private static final int MAX_RECENT_ORDERS = 10;
    private static final long EXPIRE_SECONDS = 2 * 3600; // 2 hours

    private final String redisHost;
    private final int redisPort;

    private transient JedisPool jedisPool;
    private transient ObjectMapper objectMapper;

    public RecentOrdersSink(String redisHost, int redisPort) {
        this.redisHost = redisHost;
        this.redisPort = redisPort;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(10);
        poolConfig.setMaxIdle(5);
        poolConfig.setMinIdle(1);
        jedisPool = new JedisPool(poolConfig, redisHost, redisPort);
        objectMapper = new ObjectMapper();
        LOG.info("RecentOrdersSink initialized: {}:{}", redisHost, redisPort);
    }

    @Override
    public void invoke(CoffeeOrder order, Context context) throws Exception {
        try (Jedis jedis = jedisPool.getResource()) {
            // Create order map matching the expected format
            Map<String, Object> orderMap = new LinkedHashMap<>();
            // Use hash of message_id as synthetic ID
            orderMap.put("id", Math.abs(order.getMessageId().hashCode()));
            orderMap.put("drink", order.getDrink());
            orderMap.put("store", order.getStore());
            orderMap.put("price", order.getPrice().doubleValue());
            orderMap.put("timestamp", order.getTimestamp());

            // Get existing recent orders
            String existingJson = jedis.get("orders:recent");
            List<Map<String, Object>> recentOrders = new ArrayList<>();

            if (existingJson != null && !existingJson.isEmpty()) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> existing = objectMapper.readValue(existingJson, List.class);
                recentOrders.addAll(existing);
            }

            // Add new order and keep only last 10
            recentOrders.add(orderMap);
            if (recentOrders.size() > MAX_RECENT_ORDERS) {
                recentOrders = recentOrders.subList(recentOrders.size() - MAX_RECENT_ORDERS, recentOrders.size());
            }

            // Write back to Redis
            String json = objectMapper.writeValueAsString(recentOrders);
            jedis.setex("orders:recent", EXPIRE_SECONDS, json);

            LOG.debug("Updated orders:recent with order {}", order.getMessageId());
        } catch (Exception e) {
            LOG.error("Failed to write recent order to Redis", e);
            throw e;
        }
    }

    @Override
    public void close() throws Exception {
        if (jedisPool != null) {
            jedisPool.close();
            LOG.info("RecentOrdersSink connection pool closed");
        }
        super.close();
    }
}
