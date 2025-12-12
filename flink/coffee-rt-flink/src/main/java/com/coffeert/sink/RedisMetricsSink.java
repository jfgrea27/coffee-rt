package com.coffeert.sink;

import com.coffeert.function.OrderAggregator.AggregatedMetrics;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;
import redis.clients.jedis.Pipeline;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Flink sink that writes aggregated metrics to Redis.
 * Updates the same keys as v1 aggregator for dashboard compatibility:
 * - metrics:hourly:{hour} - JSON with top_drinks, revenue, order_count
 * - metrics:top5 - JSON array of top 5 drinks
 * - orders:recent - JSON array of recent orders
 */
public class RedisMetricsSink extends RichSinkFunction<AggregatedMetrics> {
    private static final Logger LOG = LoggerFactory.getLogger(RedisMetricsSink.class);
    private static final long serialVersionUID = 1L;

    private final String redisHost;
    private final int redisPort;

    private transient JedisPool jedisPool;
    private transient ObjectMapper objectMapper;

    public RedisMetricsSink(String redisHost, int redisPort) {
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
        LOG.info("Redis connection pool initialized: {}:{}", redisHost, redisPort);
    }

    @Override
    public void invoke(AggregatedMetrics metrics, Context context) throws Exception {
        try (Jedis jedis = jedisPool.getResource()) {
            int currentHour = Instant.now().atZone(ZoneOffset.UTC).getHour();
            String hourlyKey = "metrics:hourly:" + currentHour;

            // Get existing hourly metrics to merge
            String existingHourlyJson = jedis.get(hourlyKey);
            Map<String, Long> combinedDrinkCounts = new HashMap<>(metrics.getDrinkCounts());
            double totalRevenue = metrics.getTotalRevenue().doubleValue();
            long totalOrders = metrics.getTotalOrders();

            if (existingHourlyJson != null) {
                @SuppressWarnings("unchecked")
                Map<String, Object> existing = objectMapper.readValue(existingHourlyJson, Map.class);

                // Merge drink counts
                @SuppressWarnings("unchecked")
                Map<String, Number> existingDrinkCounts = (Map<String, Number>) existing.get("drink_counts");
                if (existingDrinkCounts != null) {
                    for (Map.Entry<String, Number> entry : existingDrinkCounts.entrySet()) {
                        combinedDrinkCounts.merge(entry.getKey(), entry.getValue().longValue(), Long::sum);
                    }
                }

                // Accumulate totals
                Number existingRevenue = (Number) existing.get("revenue");
                if (existingRevenue != null) {
                    totalRevenue += existingRevenue.doubleValue();
                }
                Number existingOrderCount = (Number) existing.get("order_count");
                if (existingOrderCount != null) {
                    totalOrders += existingOrderCount.longValue();
                }
            }

            // Calculate top 5 drinks
            List<String> topDrinks = combinedDrinkCounts.entrySet().stream()
                    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                    .limit(5)
                    .map(Map.Entry::getKey)
                    .collect(Collectors.toList());

            // Build hourly metrics JSON
            Map<String, Object> hourlyMetrics = new LinkedHashMap<>();
            hourlyMetrics.put("top_drinks", topDrinks);
            hourlyMetrics.put("revenue", Math.round(totalRevenue * 100.0) / 100.0);
            hourlyMetrics.put("order_count", totalOrders);
            hourlyMetrics.put("drink_counts", combinedDrinkCounts);

            String hourlyJson = objectMapper.writeValueAsString(hourlyMetrics);
            String top5Json = objectMapper.writeValueAsString(topDrinks);

            // Update Redis using pipeline
            Pipeline pipe = jedis.pipelined();
            pipe.set(hourlyKey, hourlyJson);
            pipe.expire(hourlyKey, 25 * 3600);  // Expire after 25 hours
            pipe.set("metrics:top5", top5Json);
            pipe.sync();

            LOG.debug("Wrote metrics to Redis: {} orders, {} revenue (hour={})",
                    metrics.getTotalOrders(), metrics.getTotalRevenue(), currentHour);
        } catch (Exception e) {
            LOG.error("Failed to write metrics to Redis", e);
            throw e;
        }
    }

    @Override
    public void close() throws Exception {
        if (jedisPool != null) {
            jedisPool.close();
            LOG.info("Redis connection pool closed");
        }
        super.close();
    }
}
