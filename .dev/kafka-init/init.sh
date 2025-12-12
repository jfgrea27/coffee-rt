#!/bin/bash
set -e

echo "Waiting for Kafka to be ready..."
for i in $(seq 1 30); do
    if /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" >/dev/null 2>&1; then
        echo "Kafka is ready!"
        break
    fi
    echo "Attempt $i: Kafka not ready, waiting..."
    sleep 2
done

echo "Creating topics..."

# Create orders topic for v3 API -> Flink
# 4 partitions - one per store (uptown, downtown, central, southend)
# This allows parallel processing by store
/opt/kafka/bin/kafka-topics.sh --create \
    --topic orders \
    --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
    --partitions 4 \
    --replication-factor 1 \
    --if-not-exists

echo "Listing topics:"
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS"

echo ""
echo "Topic details:"
/opt/kafka/bin/kafka-topics.sh --describe \
    --topic orders \
    --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS"

echo ""
echo "Kafka initialization complete!"
