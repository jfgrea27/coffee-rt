package com.coffeert;

import com.coffeert.function.OrderAggregator;
import com.coffeert.model.CoffeeOrder;
import com.coffeert.sink.RecentOrdersSink;
import com.coffeert.sink.RedisMetricsSink;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.streaming.api.functions.sink.SinkFunction;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.CheckpointingMode;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.CheckpointConfig;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingProcessingTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Timestamp;

/**
 * Flink streaming job for processing v3 coffee orders.
 *
 * @version 0.1.0
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

        // Checkpointing configuration from environment
        boolean checkpointingEnabled = Boolean.parseBoolean(getEnv("CHECKPOINTING_ENABLED", "true"));
        long checkpointIntervalMs = Long.parseLong(getEnv("CHECKPOINT_INTERVAL_MS", "10000"));
        long checkpointTimeoutMs = Long.parseLong(getEnv("CHECKPOINT_TIMEOUT_MS", "60000"));
        long minPauseBetweenCheckpointsMs = Long.parseLong(getEnv("MIN_PAUSE_BETWEEN_CHECKPOINTS_MS", "1000"));
        int maxConcurrentCheckpoints = Integer.parseInt(getEnv("MAX_CONCURRENT_CHECKPOINTS", "1"));
        String checkpointDir = getEnv("CHECKPOINT_DIR", "file:///tmp/flink-checkpoints");

        LOG.info("Starting Coffee Order Flink Job");
        LOG.info("Kafka: {}:{} topic={} group={}", kafkaBootstrapServers, kafkaTopic, kafkaConsumerGroup);
        LOG.info("Postgres: {}:{}/{}", postgresHost, postgresPort, postgresDb);
        LOG.info("Redis: {}:{}", redisHost, redisPort);
        LOG.info("Checkpointing: enabled={} interval={}ms dir={}",
                checkpointingEnabled, checkpointIntervalMs, checkpointDir);

        // Create Flink execution environment
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Configure checkpointing for exactly-once semantics
        if (checkpointingEnabled) {
            configureCheckpointing(env, checkpointIntervalMs, checkpointTimeoutMs,
                    minPauseBetweenCheckpointsMs, maxConcurrentCheckpoints, checkpointDir);
        } else {
            LOG.info("Checkpointing disabled - running in max throughput mode");
        }

        // Kafka source configuration
        // With checkpointing: use committed offsets (from checkpoint), fallback to earliest for new deployment
        // Without checkpointing: start from latest to avoid reprocessing on restart
        OffsetsInitializer offsetsInitializer = checkpointingEnabled
                ? OffsetsInitializer.committedOffsets(org.apache.kafka.clients.consumer.OffsetResetStrategy.EARLIEST)
                : OffsetsInitializer.latest();

        KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
                .setBootstrapServers(kafkaBootstrapServers)
                .setTopics(kafkaTopic)
                .setGroupId(kafkaConsumerGroup)
                .setStartingOffsets(offsetsInitializer)
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

        // Sink 1: Write v3 orders to PostgreSQL (ON CONFLICT handles duplicates)
        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s?currentSchema=%s",
                postgresHost, postgresPort, postgresDb, postgresSchema);
        v3Orders.addSink(createPostgresSink(jdbcUrl, postgresSchema, postgresUser, postgresPassword))
                .name("PostgreSQL Sink");

        // Sink 2: Aggregate metrics in tumbling windows and write to Redis
        // Key by store to parallelize across 4 partitions (one per store)
        v3Orders
                .keyBy(CoffeeOrder::getStore)
                .window(TumblingProcessingTimeWindows.of(Time.seconds(windowSeconds)))
                .aggregate(new OrderAggregator())
                .addSink(new RedisMetricsSink(redisHost, redisPort))
                .name("Redis Metrics Sink");

        // Sink 3: Write recent orders to Redis for dashboard display
        v3Orders
                .addSink(new RecentOrdersSink(redisHost, redisPort))
                .name("Recent Orders Sink");

        // Execute the job
        env.execute("Coffee Order Processing (v3)");
    }

    /**
     * Configure checkpointing on the execution environment.
     *
     * @param env the Flink execution environment
     * @param intervalMs checkpoint interval in milliseconds
     * @param timeoutMs checkpoint timeout in milliseconds
     * @param minPauseMs minimum pause between checkpoints in milliseconds
     * @param maxConcurrent maximum concurrent checkpoints
     * @param checkpointDir directory for checkpoint storage
     */
    private static void configureCheckpointing(
            StreamExecutionEnvironment env,
            long intervalMs,
            long timeoutMs,
            long minPauseMs,
            int maxConcurrent,
            String checkpointDir) {

        env.enableCheckpointing(intervalMs, CheckpointingMode.EXACTLY_ONCE);

        CheckpointConfig config = env.getCheckpointConfig();
        config.setCheckpointTimeout(timeoutMs);
        config.setMinPauseBetweenCheckpoints(minPauseMs);
        config.setMaxConcurrentCheckpoints(maxConcurrent);
        config.setExternalizedCheckpointCleanup(
                CheckpointConfig.ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION);
        config.setCheckpointStorage(checkpointDir);

        LOG.info("Checkpointing configured: mode=EXACTLY_ONCE timeout={}ms minPause={}ms maxConcurrent={}",
                timeoutMs, minPauseMs, maxConcurrent);
    }

    /**
     * Create a JDBC sink for writing orders to PostgreSQL.
     */
    private static SinkFunction<CoffeeOrder> createPostgresSink(
            String jdbcUrl, String schema, String user, String password) {

        String insertSql = String.format(
                "INSERT INTO %s.orders (message_id, drink, store, price, timestamp) "
                        + "VALUES (?, ?::%s.drink_type, ?::%s.store_type, ?, ?) "
                        + "ON CONFLICT (message_id) DO NOTHING",
                schema, schema, schema);

        return JdbcSink.sink(
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
                        .withUsername(user)
                        .withPassword(password)
                        .build());
    }

    private static String getEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null ? value : defaultValue;
    }
}
