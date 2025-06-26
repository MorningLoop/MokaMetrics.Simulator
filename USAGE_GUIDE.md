# MokaMetrics.Simulator Usage Guide

## Overview

The MokaMetrics.Simulator is a **CoffeeMek Production Simulator** that simulates a coffee machine manufacturing process through multiple production stages using a stateless state machine architecture. It consumes production lots from Kafka and processes them through 4 production stages while generating realistic telemetry data.

## 🏭 Production Flow

The simulator processes coffee machine production lots through these stages:

```
Kafka Input → Queue → Fresa CNC → Tornio → Assemblaggio → Test → Complete
     ↓                    ↓           ↓            ↓          ↓
coffeemek.         coffeemek.    coffeemek.   coffeemek.  coffeemek.
orders.            telemetry.    telemetry.   telemetry.  telemetry.
new_lots           fresa_cnc    tornio       linea_       linea_
                                             assemblaggio  di_test
```

## 🚀 Quick Start

### 1. Environment Setup

**Important: Always activate the virtual environment before running the simulator!**

```bash
# Create virtual environment (only needed once)
python3 -m venv venv

# Activate virtual environment (required every time)
source venv/bin/activate  # On macOS/Linux
# OR on Windows:
# venv\Scripts\activate

# Install dependencies (only needed once or when requirements change)
pip install -r requirements.txt
```

### 2. Run the Simulator

```bash
# Make sure virtual environment is activated first!
source venv/bin/activate

# Start the simulator
python -m Simulator.main

# Or with custom config
CONFIG_PATH=custom_config.yaml python -m Simulator.main
```

### 3. Web Interface (Recommended)

The simulator now includes a web interface for easy control and monitoring:

```bash
# Make sure virtual environment is activated first!
source venv/bin/activate

# Start web interface (default port 8081)
python simulator_control.py web

# Or specify custom port
python simulator_control.py web --port 8080
```

**Web Interface Features:**
- ✅ Start/Stop simulator control
- ✅ Add lots manually with custom parameters
- 🚀 **Manual lot processing trigger** - Force start processing of queued lots
- 📊 Real-time statistics and monitoring
- 🔧 Machine utilization tracking
- 📱 Responsive design for mobile/desktop

Access at: `http://localhost:8081`

### 4. Console Interface

```bash
# Make sure virtual environment is activated first!
source venv/bin/activate

# Start console interface
python simulator_control.py console
```

### 3. Send Test Lots

```bash
# Send 5 test lots
python test_lot_sender.py --mode batch --count 5

# Send continuous lots (2 per minute)
python test_lot_sender.py --mode continuous --rate 2

# Send continuous lots for 10 minutes
python test_lot_sender.py --mode continuous --rate 5 --duration 10
```

### 4. Monitor Health

```bash
# Check simulator health
curl http://localhost:8080/health
```

## 📊 Architecture Components

### 1. **Kafka Consumer** 
- Reads new lots from `coffeemek.orders.new_lots`
- Automatically handles connection and reconnection

### 2. **Production Coordinator** 
- State machine managing lot flow through production stages
- Handles machine allocation and queue management

### 3. **Machine Pool** 
- Manages available machines per location (Italia, Brasile, Vietnam)
- Tracks machine status and availability

### 4. **Stage Queues** 
- FIFO queues between production stages
- Priority-based processing (high priority lots first)

### 5. **Machine Simulators** 
- Generate realistic telemetry data for each machine type
- Simulate processing times and potential machine blocks

## 🔧 Configuration

### Machine Configuration (config.yaml)
```yaml
machines:
  Italia:
    fresa_cnc: 3
    tornio: 2
    linea_assemblaggio: 1
    linea_test: 1
  Brasile:
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

## 📨 Message Formats

### Input Lot Format (from Kafka)
```json
{
  "codice_lotto": "L-2025-0001",
  "cliente": "Acme Corp",
  "quantita": 100,
  "location": "Italia",
  "priorita": "normale",
  "timestamp": "2025-06-25T10:00:00Z"
}
```

### Telemetry Output (to Kafka)
Each machine sends telemetry data to its specific topic:
- `coffeemek.telemetry.fresa_cnc`
- `coffeemek.telemetry.tornio`
- `coffeemek.telemetry.assemblaggio`
- `coffeemek.telemetry.test`

## 🎯 Key Features

- **Stateless Design**: No persistence, restart means fresh start
- **Priority Queue**: High priority lots processed first
- **Location-Based Processing**: Lots processed in their specified location
- **Machine Availability**: Lots wait if no machine available
- **Realistic Timing**: Variable processing times per stage
- **Event Stream**: All state changes sent to Kafka
- **Health Monitoring**: HTTP health check endpoint

## 🔧 Troubleshooting

### Simulator Won't Start
- Check Python virtual environment is activated
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Kafka broker connectivity

### No Lots Being Processed
- Verify lots are being sent to `coffeemek.orders.new_lots`
- Check machine availability in logs
- Ensure Kafka consumer is connected

### Connection Issues
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

### Lots Stay Queued and Don't Start Processing

If you notice that lots are added to the queue but don't start processing automatically, this is a known issue that has been fixed. Here are the solutions:

#### Solution 1: Use the Web Interface Manual Start (Recommended)
1. Open the web interface: `http://localhost:8081`
2. Add lots using the "Add New Lot" form
3. Click the **🚀 Start Processing Queued Lots** button to manually trigger processing

#### Solution 2: Check Machine Availability
Ensure machines are available for the location you're sending lots to:
```bash
# Check machine configuration in logs when simulator starts
# Default configuration:
# Italia: 2 fresa_cnc, 2 tornio, 1 assemblaggio, 1 test
# Brasile: 2 fresa_cnc, 3 tornio, 2 assemblaggio, 1 test  
# Vietnam: 4 fresa_cnc, 3 tornio, 2 assemblaggio, 2 test
```

#### Solution 3: Monitor Queue Status
Use the web interface or logs to monitor queue status:
- The web interface shows real-time queue sizes
- Console logs show queue processing attempts every second
- Health endpoint shows current status: `curl http://localhost:8080/health`

#### Technical Details
The issue was caused by the QUEUED stage not having a proper machine type mapping. The fix includes:
- Added proper stage-to-machine mapping for QUEUED lots
- Improved queue processing logic to handle lot transitions correctly
- Added manual processing trigger for immediate lot processing

### Virtual Environment Issues

**Always activate the virtual environment before running any commands:**
```bash
# Check if venv is activated (you should see (venv) in your prompt)
which python  # Should point to venv/bin/python

# If not activated:
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

### Dependencies Issues
```bash
# Reinstall dependencies if you get import errors
pip install --upgrade -r requirements.txt

# Check specific packages
pip install aiokafka aiohttp aiohttp-cors pytz
```

---

*Need more help? Check the logs for detailed error messages and processing status.*

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Production Status
The simulator logs production status every minute showing active lots and queue states.

### Kafka Topics Monitoring
```bash
# View telemetry data
kafka-console-consumer --bootstrap-server 165.227.168.240:9093 \
  --topic coffeemek.telemetry.fresa_cnc --from-beginning
```

## 🧪 Testing

### Run Basic Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run tests (if available)
pytest

# Manual testing with test script
python test_lot_sender.py --mode batch --count 10
```

## 📝 Project Structure

```
MokaMetrics.Simulator/
├── Simulator/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── models.py            # Data models
│   ├── kafka_integration.py # Kafka producer/consumer
│   ├── state_machine.py     # Production coordinator
│   └── Machine/
│       ├── __init__.py      # Machine factory
│       ├── base.py          # Base machine class
│       ├── fresa_cnc.py     # Fresa CNC simulator
│       ├── tornio.py        # Tornio simulator
│       ├── assemblaggio.py  # Assembly simulator
│       └── test.py          # Test line simulator
├── test_lot_sender.py       # Test utility
├── requirements.txt         # Dependencies
├── config.yaml             # Configuration
├── dockerfile              # Container build
└── USAGE_GUIDE.md          # This file
```
