#!/bin/sh
set -e

if [ "$REDIS_INIT" = "false" ]; then
    echo "Redis initialization skipped"
    exit 0
fi

echo "Initializing Redis with default keys..."

HOUR=$(date +"%H" | sed 's/^0//')

# metrics:hourly:{hour} - Empty hourly metrics for current hour
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SET "metrics:hourly:$HOUR" '{"top_drinks":[],"revenue":0.0,"order_count":0}'
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" EXPIRE "metrics:hourly:$HOUR" 90000

# metrics:top5 - Empty top 5 drinks list
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SET "metrics:top5" '[]'

# orders:recent - Empty recent orders list
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SET "orders:recent" '[]'
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" EXPIRE "orders:recent" 7200

echo "Redis initialization completed successfully"
