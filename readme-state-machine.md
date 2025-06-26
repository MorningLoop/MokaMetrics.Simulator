# CoffeeMek Production Simulator - State Machine Version

Production simulator that consumes lots from Kafka and processes them through 4 production stages using a stateless state machine.

## 🏭 Production Flow

```
Kafka Input → Queue → Fresa CNC → Tornio → Assemblaggio → Test → Complete
     ↓                    ↓           ↓            ↓          ↓
coffeemek.         coffeemek.    coffeemek.   coffeemek.  coffeemek.
orders.            telemetry.    telemetry.   telemetry.  telemetry.
new_lots           fresa_cnc    tornio       linea_       linea_
                                             assemblaggio  di_test
```

## 📊 Architecture

### Components:
1. **Kafka Consumer** - Reads new lots from `coffeemek.orders.new_lots`
2. **Production Coordinator** - State machine managing lot flow
3. **Machine Pool** - Manages available machines per location
4. **Stage Queues** - FIFO queues between production stages
5. **Machine Simulators** - Generate telemetry data for each machine type

### State Flow:
- **QUEUED** → Waiting to start production
- **FRESA_CNC** → Being processed by Fresa CNC
- **TORNIO** → Being processed by Tornio
- **ASSEMBLAGGIO** → Being processed by Assembly Line
- **TEST** → Being tested
- **COMPLETED** → Production complete

## 🚀 Quick Start

### 1. Run the Simulator

```bash
# Using Docker
docker build -t coffeemek-simulator .
docker run -d --name coffeemek-simulator -p 8080:8080 coffeemek-simulator

# Or using Python directly
pip install -r requirements.txt
python -m simulator.main
```

### 2. Send Test Lots

```bash
# Send 5 test lots
python test_lot_sender.py --mode batch --count 5

# Send continuous lots (2 per minute)
python test_lot_sender.py --mode continuous --rate 2
```

## 📨 Message Formats

### Input Lot Format (from Kafka)
```json
{
  "codice_lotto": "L-2024-0001",
  "cliente": "Acme Corp",
  "quantita": 100,
  "location": "Italy",
  "priorita": "normale",
  "timestamp": "2024-12-20T10:00:00Z"
}
```

### Telemetry Output (to Kafka)
Each machine sends telemetry data to its specific topic:
- `coffeemek.telemetry.fresa_cnc`
- `coffeemek.telemetry.tornio_automatico`
- `coffeemek.telemetry.linea_assemblaggio`
- `coffeemek.telemetry.linea_di_test`

### Production Events (to Kafka)
Sent to `coffeemek.events.production_status`:
```json
{
  "event_type": "fresa_cnc.started",
  "data": {
    "codice_lotto": "L-2024-0001",
    "machine_id": "cnc_milling_Italy_1",
    "processing_time_seconds": 2400,
    "timestamp": "2024-12-20T10:05:00Z"
  }
}
```

## 🔧 Configuration

### Machine Configuration (config.yaml)
```yaml
machines:
  Italy:
    fresa_cnc: 3
    tornio: 2
    linea_assemblaggio: 1
    linea_test: 1
  Brazil:
    fresa_cnc: 2
    tornio: 3
    linea_assemblaggio: 2
    linea_test: 1
  Vietnam:
    fresa_cnc: 4
    tornio: 3
    linea_assemblaggio: 2
    linea_test: 2
```

### Processing Times
- **Fresa CNC**: 20-60 minutes
- **Tornio**: 15-45 minutes
- **Assemblaggio**: 30-90 minutes
- **Test**: 10-30 minutes

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Production Status
The simulator logs production status every minute:
```
Production Status: 5 active lots
  queued: 2 lots waiting
  fresa_cnc: 1 lots waiting
  tornio: 0 lots waiting
```

### Kafka Topics Monitoring
```bash
# View lots being processed
kafka-console-consumer --bootstrap-server 165.227.168.240:9093 \
  --topic coffeemek.telemetry.fresa_cnc --from-beginning

# View production events
kafka-console-consumer --bootstrap-server 165.227.168.240:9093 \
  --topic coffeemek.events.production_status --from-beginning
```

## 🎯 Features

- **Stateless Design**: No persistence, restart means fresh start
- **Priority Queue**: High priority lots processed first
- **Location-Based Processing**: Lots processed in their specified location
- **Machine Availability**: Lots wait if no machine available
- **Realistic Timing**: Variable processing times per stage
- **Event Stream**: All state changes sent to Kafka

## 🐛 Troubleshooting

### No lots being processed
- Check Kafka consumer is connected: Look for "Kafka consumer started" in logs
- Verify lots are being sent to `coffeemek.orders.new_lots`
- Check machine availability in logs

### Lots stuck in queue
- Verify machines are initialized for the lot's location
- Check if machines are blocked (5% random chance)
- Look for error messages in logs

### Connection issues
```bash
# Test Kafka connection
python -c "
from aiokafka import AIOKafkaProducer
import asyncio
async def test():
    p = AIOKafkaProducer(bootstrap_servers='165.227.168.240:9093')
    await p.start()
    print('Connected!')
    await p.stop()
asyncio.run(test())
"
```

## 📝 Project Structure

```
coffeemek-simulator/
├── simulator/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── models.py            # Data models
│   ├── kafka_integration.py # Kafka producer/consumer
│   ├── state_machine.py     # Production coordinator
│   └── machines/
│       ├── __init__.py      # Machine factory
│       ├── base.py          # Base machine class
│       ├── fresa_cnc.py     # Fresa CNC simulator
│       ├── tornio.py        # Tornio simulator
│       ├── assemblaggio.py  # Assembly simulator
│       └── test.py          # Test line simulator
├── test_lot_sender.py       # Test utility
├── requirements.txt         # Dependencies
├── Dockerfile              # Container build
└── config.yaml             # Configuration
```