#!/bin/bash
set -e

# MokaMetrics Simulator Docker Entrypoint Script

echo "🚀 Starting MokaMetrics Simulator..."
echo "📊 Kafka Broker: ${KAFKA_BROKER:-165.227.168.240:29093}"
echo "🏥 Health Check Port: ${HEALTH_CHECK_PORT:-8083}"
echo "📝 Log Level: ${LOG_LEVEL:-INFO}"

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Wait for Kafka to be available (optional)
if [ "${WAIT_FOR_KAFKA:-false}" = "true" ]; then
    echo "⏳ Waiting for Kafka to be available..."
    timeout 60 bash -c 'until nc -z ${KAFKA_BROKER%:*} ${KAFKA_BROKER#*:}; do sleep 1; done'
    echo "✅ Kafka is available"
fi

# Execute the main command
echo "🎯 Starting simulator with command: $@"
exec "$@"
