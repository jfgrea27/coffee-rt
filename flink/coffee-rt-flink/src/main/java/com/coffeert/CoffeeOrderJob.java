package com.coffeert;

import com.coffeert.function.OrderAggregator;
import com.coffeert.model.CoffeeOrder;
import com.coffeert.sink.RedisMetricsSink;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingProcessingTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Timestamp;

/**
 * Flink streaming job for processing v3 coffee orders.
 *
 * This job:
 * 1. Consumes orders from Kafka (topic: orders)
 * 2. Filters for v3 orders only
 * 3. Writes all orders to PostgreSQL (replacing kafka-worker)
 * 4. Aggregates metrics and writes to Redis (replacing kafka-aggregator)
 */
public final class CoffeeOrderJob {
    private static final Logger LOG = LoggerFactory.getLogger(CoffeeOrderJob.class);
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    private CoffeeOrderJob() {
        // Utility class - prevent instantiation
    }

    public static void main(String[] args) throws Exception {
        // Configuration from environment variables
        String kafkaBootstrapServers = getEnv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092");
        String kafkaTopic = getEnv("KAFKA_TOPIC", "orders");
        String kafkaConsumerGroup = getEnv("KAFKA_CONSUMER_GROUP", "flink-processors");

        String postgresHost = getEnv("POSTGRES_HOST", "postgres");
        String postgresPort = getEnv("POSTGRES_PORT", "5432");
        String postgresDb = getEnv("POSTGRES_DB", "coffee-rt");
        String postgresUser = getEnv("POSTGRES_USER", "coffee-rt");
        String postgresPassword = getEnv("POSTGRES_PASSWORD", "coffee-rt_password");
        String postgresSchema = getEnv("POSTGRES_SCHEMA", "coffee_rt");

        String redisHost = getEnv("REDIS_HOST", "redis");
        int redisPort = Integer.parseInt(getEnv("REDIS_PORT", "6379"));

        int windowSeconds = Integer.parseInt(getEnv("WINDOW_SECONDS", "1"));

        LOG.info("Starting Coffee Order Flink Job (no checkpointing - max throughput mode)");
        LOG.info("Kafka: {}:{} topic={} group={}", kafkaBootstrapServers, kafkaTopic, kafkaConsumerGroup);
        LOG.info("Postgres: {}:{}/{}", postgresHost, postgresPort, postgresDb);
        LOG.info("Redis: {}:{}", redisHost, redisPort);

        // Create Flink execution environment
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // No checkpointing - maximum throughput mode
        // Trade-off: On restart, may reprocess or lose some messages
        // PostgreSQL ON CONFLICT handles duplicates safely

        // Kafka source - start from earliest on each restart
        KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
                .setBootstrapServers(kafkaBootstrapServers)
                .setTopics(kafkaTopic)
                .setGroupId(kafkaConsumerGroup)
                .setStartingOffsets(OffsetsInitializer.latest())  // Start from latest on restart
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();

        // Read from Kafka and parse JSON
        DataStream<CoffeeOrder> orders = env
                .fromSource(kafkaSource, WatermarkStrategy.noWatermarks(), "Kafka Source")
                .map(json -> {
                    try {
                        return MAPPER.readValue(json, CoffeeOrder.class);
                    } catch (Exception e) {
                        LOG.warn("Failed to parse order JSON: {}", json, e);
                        return null;
                    }
                })
                .filter(order -> order != null)
                .name("Parse JSON");

        // Filter for v3 orders only
        DataStream<CoffeeOrder> v3Orders = orders
                .filter(order -> "v3".equals(order.getVersion()))
                .name("Filter v3");

        // No deduplication - PostgreSQL ON CONFLICT handles duplicates
        // This maximizes throughput by avoiding keyed state overhead

        // JDBC connection string
        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s?currentSchema=%s",
                postgresHost, postgresPort, postgresDb, postgresSchema);

        // Sink 1: Write v3 orders to PostgreSQL
        // ON CONFLICT handles any duplicates from retries/restarts
        String insertSql = String.format(
                "INSERT INTO %s.orders (message_id, drink, store, price, timestamp) " +
                "VALUES (?, ?::%s.drink_type, ?::%s.store_type, ?, ?) " +
                "ON CONFLICT (message_id) DO NOTHING",
                postgresSchema, postgresSchema, postgresSchema);
        v3Orders.addSink(JdbcSink.sink(
                insertSql,
                (statement, order) -> {
                    statement.setString(1, order.getMessageId());
                    statement.setString(2, order.getDrink());
                    statement.setString(3, order.getStore());
                    statement.setBigDecimal(4, order.getPrice());
                    statement.setTimestamp(5, Timestamp.from(order.getTimestampAsInstant()));
                },
                JdbcExecutionOptions.builder()
                        .withBatchSize(100)
                        .withBatchIntervalMs(200)
                        .withMaxRetries(3)
                        .build(),
                new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                        .withUrl(jdbcUrl)
                        .withDriverName("org.postgresql.Driver")
                        .withUsername(postgresUser)
                        .withPassword(postgresPassword)
                        .build()
        )).name("PostgreSQL Sink");

        // Sink 2: Aggregate metrics in tumbling windows and write to Redis
        // Key by store to parallelize across 4 partitions (one per store)
        v3Orders
                .keyBy(CoffeeOrder::getStore)
                .window(TumblingProcessingTimeWindows.of(Time.seconds(windowSeconds)))
                .aggregate(new OrderAggregator())
                .addSink(new RedisMetricsSink(redisHost, redisPort))
                .name("Redis Metrics Sink");

        // Execute the job
        env.execute("Coffee Order Processing (v3)");
    }

    private static String getEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null ? value : defaultValue;
    }
}
