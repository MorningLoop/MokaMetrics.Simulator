#!/bin/bash

# CoffeeMek Production Simulator - Example Run Script

echo "🏭 CoffeeMek Production Simulator - State Machine Example"
echo "========================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Build and start the simulator
echo -e "${YELLOW}Step 1: Building and starting the simulator...${NC}"
docker build -t coffeemek-simulator . || {
    echo -e "${RED}Build failed!${NC}"
    exit 1
}

docker stop coffeemek-simulator 2>/dev/null || true
docker rm coffeemek-simulator 2>/dev/null || true

docker run -d \
    --name coffeemek-simulator \
    -p 8080:8080 \
    coffeemek-simulator || {
    echo -e "${RED}Failed to start simulator!${NC}"
    exit 1
}

echo -e "${GREEN}✅ Simulator started${NC}"
echo ""

# Step 2: Wait for simulator to be ready
echo -e "${YELLOW}Step 2: Waiting for simulator to be ready...${NC}"
sleep 5

# Check health
if curl -f -s http://localhost:8080/health > /dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    docker logs coffeemek-simulator
    exit 1
fi
echo ""

# Step 3: Send test lots
echo -e "${YELLOW}Step 3: Sending test lots to Kafka...${NC}"
echo "This will send 10 test lots to the production queue"
echo ""

# Create a simple Python script to send lots
cat > send_lots_temp.py << 'EOF'
import asyncio
import json
from datetime import datetime
from aiokafka import AIOKafkaProducer
import random

async def main():
    producer = AIOKafkaProducer(
        bootstrap_servers="165.227.168.240:9093",
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await producer.start()
    
    locations = ["Italy", "Brazil", "Vietnam"]
    clienti = ["Lavazza", "Illy", "Segafredo", "Kimbo", "Vergnano"]
    
    for i in range(10):
        lot = {
            "codice_lotto": f"L-DEMO-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}",
            "cliente": random.choice(clienti),
            "quantita": random.randint(100, 300),
            "location": random.choice(locations),
            "priorita": "alta" if i < 2 else "normale"
        }
        
        await producer.send_and_wait(
            topic="coffeemek.orders.new_lots",
            key=lot["codice_lotto"].encode('utf-8'),
            value=lot
        )
        
        print(f"Sent: {lot['codice_lotto']} - {lot['cliente']} - {lot['location']} - Priority: {lot['priorita']}")
        await asyncio.sleep(0.5)
    
    await producer.stop()
    print("\n✅ All lots sent!")

asyncio.run(main())
EOF

python send_lots_temp.py || {
    echo -e "${RED}Failed to send lots${NC}"
    rm send_lots_temp.py
    exit 1
}

rm send_lots_temp.py
echo ""

# Step 4: Monitor production
echo -e "${YELLOW}Step 4: Monitoring production flow...${NC}"
echo "Showing simulator logs for 30 seconds..."
echo ""

# Show logs with timeout
timeout 30s docker logs -f coffeemek-simulator 2>&1 | grep -E "(lot|machine|Production Status)" &

# Wait
sleep 30

echo ""
echo -e "${YELLOW}Step 5: Production Statistics${NC}"
echo "==============================="

# Get production status via health endpoint
curl -s http://localhost:8080/metrics 2>/dev/null || echo "Metrics not available"

echo ""
echo -e "${GREEN}✅ Demo Complete!${NC}"
echo ""
echo "📊 To continue monitoring:"
echo "   - Logs: docker logs -f coffeemek-simulator"
echo "   - Health: curl http://localhost:8080/health"
echo "   - Stop: docker stop coffeemek-simulator"
echo ""
echo "📨 To send more lots:"
echo "   - python test_lot_sender.py --mode batch --count 20"
echo "   - python test_lot_sender.py --mode continuous --rate 5"
echo ""