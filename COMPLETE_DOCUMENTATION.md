# MokaMetrics.Simulator - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [API Reference](#api-reference)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Development](#development)
10. [Deployment](#deployment)

## Project Overview

### What is MokaMetrics.Simulator?

The **MokaMetrics.Simulator** is a sophisticated **CoffeeMek Production Simulator** that simulates a complete coffee machine manufacturing process. It implements a stateless state machine architecture to process production lots through multiple manufacturing stages while generating realistic telemetry data.

### Key Capabilities

- **Real-time Production Simulation**: Processes coffee machine production lots through 4 manufacturing stages
- **Kafka Integration**: Consumes orders and produces telemetry data via Kafka messaging
- **Multi-location Support**: Simulates production across 3 global locations (Italia, Brasile, Vietnam)
- **Machine Pool Management**: Manages 26+ machines across different types and locations
- **Priority Processing**: Handles high-priority lots with precedence
- **Realistic Timing**: Variable processing times based on actual manufacturing data
- **Health Monitoring**: Built-in health check and monitoring capabilities

### Business Value

- **Production Planning**: Test and validate production workflows
- **Capacity Planning**: Understand machine utilization and bottlenecks
- **Data Pipeline Testing**: Validate Kafka data flows and processing
- **Training**: Safe environment for operator training
- **Integration Testing**: Test downstream systems with realistic data

## Architecture

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kafka Input   │───▶│  State Machine   │───▶│  Kafka Output   │
│  (New Lots)     │    │   Coordinator    │    │  (Telemetry)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Machine Pool   │
                       │  Management      │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Health Check    │
                       │    Server        │
                       └──────────────────┘
```

### Production Flow

```
Kafka Input → Queue → Fresa CNC → Tornio → Assemblaggio → Test → Complete
     ↓                    ↓           ↓            ↓          ↓
coffeemek.         coffeemek.    coffeemek.   coffeemek.  coffeemek.
orders.            telemetry.    telemetry.   telemetry.  telemetry.
new_lots           fresa_cnc    tornio       linea_       linea_
                                             assemblaggio  di_test
```

### State Machine States

1. **QUEUED**: Waiting to start production
2. **FRESA_CNC**: CNC milling process (20-60 minutes)
3. **TORNIO**: Automatic lathe process (15-45 minutes)
4. **ASSEMBLAGGIO**: Assembly line process (30-90 minutes)
5. **TEST**: Quality testing process (10-30 minutes)
6. **COMPLETED**: Production finished

### Machine Distribution

| Location | Fresa CNC | Tornio | Assemblaggio | Test | Total |
|----------|-----------|--------|--------------|------|-------|
| Italia   | 3         | 2      | 1            | 1    | 7     |
| Brasile  | 2         | 3      | 2            | 1    | 8     |
| Vietnam  | 4         | 3      | 2            | 2    | 11    |
| **Total**| **9**     | **8**  | **5**        | **4**| **26**|

## Installation & Setup

### Prerequisites

- Python 3.11 or higher
- Access to Kafka broker (default: 165.227.168.240:9093)
- 8GB RAM recommended
- Network connectivity for Kafka and API endpoints

### Step-by-Step Installation

1. **Clone and Navigate to Project**
   ```bash
   cd /path/to/MokaMetrics.Simulator
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Verify Installation**
   ```bash
   python test_simulator.py
   ```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| aiokafka | >=0.8.0 | Kafka async client |
| aiohttp | >=3.8.0 | HTTP server/client |
| PyYAML | >=6.0 | Configuration parsing |
| pytz | >=2023.3 | Timezone handling |
| requests | >=2.31.0 | HTTP requests |
| ujson | >=5.7.0 | Fast JSON processing |
| pytest | >=7.4.0 | Testing framework |
| pytest-asyncio | >=0.21.0 | Async testing |

## Configuration

### Main Configuration (config.yaml)

```yaml
# Kafka Configuration
kafka:
  bootstrap_servers: "165.227.168.240:9093"
  topics:
    input: "coffeemek.orders.new_lots"
    telemetry_prefix: "coffeemek.telemetry"
    events: "coffeemek.events.production_status"

# API Configuration
api:
  endpoint_url: "https://mokametrics-api-fafshjgtf4degege.italynorth-01.azurewebsites.net"
  api_key: ""  # Set via MOKAMETRICS_API_KEY environment variable
  enable_api: false  # Set via ENABLE_API environment variable

# Health Check Configuration
health_check:
  port: 8080

# Machine Configuration by Location
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

# Processing Time Configuration (in seconds)
processing_times:
  fresa_cnc:
    min: 1200  # 20 minutes
    max: 3600  # 60 minutes
  tornio:
    min: 900   # 15 minutes
    max: 2700  # 45 minutes
  assemblaggio:
    min: 1800  # 30 minutes
    max: 5400  # 90 minutes
  test:
    min: 600   # 10 minutes
    max: 1800  # 30 minutes

# Simulation Parameters
simulation:
  status_report_interval: 60  # seconds
  machine_block_probability: 0.05  # 5% chance of machine blocking
  priority_processing: true  # Process high priority lots first
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_PATH` | config.yaml | Path to configuration file |
| `MOKAMETRICS_API_KEY` | "" | API key for external API |
| `ENABLE_API` | false | Enable external API integration |
| `HEALTH_CHECK_PORT` | 8080 | Health check server port |

## Usage

### Starting the Simulator

```bash
# Basic startup
source venv/bin/activate
python -m Simulator.main

# With custom configuration
CONFIG_PATH=custom_config.yaml python -m Simulator.main

# With environment variables
HEALTH_CHECK_PORT=9090 ENABLE_API=true python -m Simulator.main
```

### Sending Test Lots

```bash
# Send 5 test lots
python test_lot_sender.py --mode batch --count 5

# Send continuous lots (2 per minute)
python test_lot_sender.py --mode continuous --rate 2

# Send continuous lots for 10 minutes
python test_lot_sender.py --mode continuous --rate 5 --duration 10

# Use custom Kafka broker
python test_lot_sender.py --broker localhost:9092 --mode batch --count 10
```

### Monitoring

```bash
# Health check
curl http://localhost:8080/health

# Continuous monitoring
watch -n 5 'curl -s http://localhost:8080/health | jq'

# Check simulator logs
tail -f simulator.log
```

## API Reference

### Health Check Endpoint

**GET** `/health`

Returns simulator health status and metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-25T15:08:57.686140",
  "uptime_seconds": 24.964127,
  "kafka_broker": "165.227.168.240:9093"
}
```

### Input Message Format

**Topic:** `coffeemek.orders.new_lots`

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

**Fields:**
- `codice_lotto`: Unique lot identifier
- `cliente`: Customer name
- `quantita`: Quantity to produce
- `location`: Production location (Italia/Brasile/Vietnam)
- `priorita`: Priority level (normale/alta/bassa)
- `timestamp`: ISO 8601 timestamp

### Output Telemetry Format

**Topics:** 
- `coffeemek.telemetry.fresa_cnc`
- `coffeemek.telemetry.tornio`
- `coffeemek.telemetry.assemblaggio`
- `coffeemek.telemetry.test`

**Example Fresa CNC Telemetry:**
```json
{
  "codice_lotto": "L-2025-0001",
  "luogo": "Italia",
  "timestamp_locale": "2025-06-25T16:30:00+01:00",
  "timestamp_utc": "2025-06-25T15:30:00Z",
  "blocco_macchina": false,
  "motivo_blocco": null,
  "ultima_manutenzione": "2025-06-20T10:00:00Z",
  "macchina": "Fresa CNC",
  "tempo_ciclo": 45.5,
  "profondita_taglio": 2.3,
  "vibrazione": 0.15,
  "allarmi_utente": "Nessuno"
}
```

## Testing

### Automated Testing

```bash
# Run comprehensive test suite
python test_simulator.py

# Run unit tests (if available)
pytest

# Test specific functionality
python -m pytest tests/ -v
```

### Manual Testing

```bash
# 1. Start simulator
python -m Simulator.main

# 2. In another terminal, send test lots
python test_lot_sender.py --mode batch --count 3

# 3. Monitor health
curl http://localhost:8080/health

# 4. Check Kafka topics (if kafka tools available)
kafka-console-consumer --bootstrap-server 165.227.168.240:9093 \
  --topic coffeemek.telemetry.fresa_cnc --from-beginning
```

### Test Scenarios

1. **Basic Functionality Test**
   - Start simulator
   - Send 5 test lots
   - Verify health endpoint
   - Check telemetry output

2. **Load Testing**
   - Send continuous lots at high rate (10/minute)
   - Monitor machine utilization
   - Verify no memory leaks

3. **Priority Testing**
   - Send mix of normal and high priority lots
   - Verify high priority lots processed first

4. **Location Testing**
   - Send lots to different locations
   - Verify location-specific processing

5. **Error Handling**
   - Disconnect Kafka broker
   - Verify graceful degradation
   - Test reconnection logic

## Troubleshooting

### Common Issues

#### 1. Simulator Won't Start

**Symptoms:**
- Import errors
- Module not found errors
- Connection failures

**Solutions:**
```bash
# Check virtual environment
source venv/bin/activate
which python

# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.11+

# Fix file naming issues
ls Simulator/  # Should see kafka_integration.py, state_machine.py
```

#### 2. Kafka Connection Issues

**Symptoms:**
- "Failed to start Kafka producer"
- Connection timeout errors

**Solutions:**
```bash
# Test Kafka connectivity
telnet 165.227.168.240 9093

# Check firewall/network
ping 165.227.168.240

# Use alternative broker
python -m Simulator.main --broker localhost:9092
```

#### 3. No Lots Being Processed

**Symptoms:**
- Health check shows 0 active lots
- No telemetry data generated

**Solutions:**
```bash
# Verify lots are being sent
python test_lot_sender.py --mode batch --count 1

# Check machine availability
grep "machine" simulator.log

# Verify topic names
# Input: coffeemek.orders.new_lots
# Output: coffeemek.telemetry.*
```

#### 4. Memory/Performance Issues

**Symptoms:**
- High memory usage
- Slow processing
- Timeouts

**Solutions:**
```bash
# Monitor resources
top -p $(pgrep -f "Simulator.main")

# Reduce machine count in config.yaml
# Increase processing times
# Check for memory leaks in logs
```

### Debug Mode

```bash
# Enable debug logging
export PYTHONPATH=/path/to/simulator
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
" -m Simulator.main
```

### Log Analysis

```bash
# Filter important logs
grep -E "(ERROR|WARN|machine|lot)" simulator.log

# Monitor real-time
tail -f simulator.log | grep -E "(lot|machine|health)"

# Count processed lots
grep "lot.*completed" simulator.log | wc -l
```

## Development

### Project Structure

```
MokaMetrics.Simulator/
├── Simulator/                    # Main package
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # Entry point and orchestration
│   ├── models.py                # Data models and enums
│   ├── kafka_integration.py     # Kafka producer/consumer
│   ├── state_machine.py         # Production coordinator
│   └── Machine/                 # Machine simulators
│       ├── __init__.py          # Machine factory
│       ├── base.py              # Abstract base class
│       ├── fresa_cnc.py         # CNC milling simulator
│       ├── tornio.py            # Lathe simulator
│       ├── assemblaggio.py      # Assembly line simulator
│       └── test.py              # Test line simulator
├── test_lot_sender.py           # Test utility for sending lots
├── test_simulator.py            # Comprehensive test suite
├── requirements.txt             # Python dependencies
├── config.yaml                  # Configuration file
├── dockerfile                   # Container build instructions
├── example-run.sh               # Example run script
├── USAGE_GUIDE.md              # User guide
├── COMPLETE_DOCUMENTATION.md    # This file
└── venv/                       # Virtual environment (created)
```

### Key Classes

#### 1. CoffeeMekSimulator (main.py)
- **Purpose**: Main orchestrator class
- **Responsibilities**: Coordinate all components, handle startup/shutdown
- **Key Methods**: `start()`, `stop()`, `_status_reporter()`

#### 2. ProductionCoordinator (state_machine.py)
- **Purpose**: State machine managing lot flow
- **Responsibilities**: Queue management, machine allocation, state transitions
- **Key Methods**: `add_lot()`, `process_lots()`, `_transition_lot()`

#### 3. KafkaDataSender (kafka_integration.py)
- **Purpose**: Kafka integration layer
- **Responsibilities**: Consume lots, produce telemetry, API integration
- **Key Methods**: `consume_lots()`, `send_to_kafka()`, `send_to_api()`

#### 4. MachinePool (state_machine.py)
- **Purpose**: Machine resource management
- **Responsibilities**: Track machine availability, allocation, status
- **Key Methods**: `get_available_machine()`, `release_machine()`, `get_machine_status()`

### Adding New Machine Types

1. **Create Machine Simulator**
   ```python
   # Simulator/Machine/new_machine.py
   from .base import MachineSimulator

   class NewMachineSimulator(MachineSimulator):
       def generate_data(self):
           # Implementation
           pass

       def get_processing_time(self):
           # Implementation
           pass
   ```

2. **Update Configuration**
   ```yaml
   # config.yaml
   machines:
     Italia:
       new_machine: 2
   ```

3. **Update State Machine**
   ```python
   # Add to stage_to_machine mapping
   self.stage_to_machine[ProductionStage.NEW_STAGE] = "new_machine"
   ```

### Adding New Locations

1. **Update Models**
   ```python
   # Simulator/models.py
   class Location(Enum):
       NEW_LOCATION = ("NewLocation", "Timezone/Name")
   ```

2. **Update Configuration**
   ```yaml
   # config.yaml
   machines:
     NewLocation:
       fresa_cnc: 2
       # ... other machines
   ```

### Code Style Guidelines

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Document all classes and methods
- **Async/Await**: Use async patterns consistently
- **Error Handling**: Implement comprehensive error handling
- **Logging**: Use structured logging with appropriate levels

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t mokametrics-simulator .

# Run container
docker run -d \
  --name mokametrics-simulator \
  -p 8080:8080 \
  -e MOKAMETRICS_API_KEY=your_key \
  mokametrics-simulator

# Check logs
docker logs -f mokametrics-simulator

# Stop container
docker stop mokametrics-simulator
```

### Production Deployment

#### 1. Environment Setup
```bash
# Production server setup
sudo apt update
sudo apt install python3.11 python3.11-venv

# Create production user
sudo useradd -m -s /bin/bash mokametrics
sudo su - mokametrics

# Setup application
git clone https://github.com/your-org/MokaMetrics.Simulator.git
cd MokaMetrics.Simulator
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Systemd Service
```ini
# /etc/systemd/system/mokametrics-simulator.service
[Unit]
Description=MokaMetrics Production Simulator
After=network.target

[Service]
Type=simple
User=mokametrics
WorkingDirectory=/home/mokametrics/MokaMetrics.Simulator
Environment=PATH=/home/mokametrics/MokaMetrics.Simulator/venv/bin
ExecStart=/home/mokametrics/MokaMetrics.Simulator/venv/bin/python -m Simulator.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Monitoring Setup
```bash
# Enable and start service
sudo systemctl enable mokametrics-simulator
sudo systemctl start mokametrics-simulator

# Monitor status
sudo systemctl status mokametrics-simulator

# View logs
sudo journalctl -u mokametrics-simulator -f
```

### Scaling Considerations

#### Horizontal Scaling
- **Multiple Instances**: Run multiple simulator instances with different consumer groups
- **Load Balancing**: Use nginx or similar for health check load balancing
- **Kafka Partitioning**: Increase topic partitions for parallel processing

#### Vertical Scaling
- **Memory**: 8GB+ recommended for high-throughput scenarios
- **CPU**: Multi-core beneficial for async processing
- **Network**: Ensure sufficient bandwidth for Kafka traffic

#### Performance Tuning
```yaml
# config.yaml optimizations
kafka:
  batch_size: 16384
  linger_ms: 10
  compression_type: "gzip"

simulation:
  status_report_interval: 30  # Reduce reporting frequency
  batch_processing: true      # Process lots in batches
```

### Security Considerations

#### 1. Network Security
- **Firewall**: Restrict access to necessary ports only
- **VPN**: Use VPN for Kafka broker access
- **TLS**: Enable TLS for Kafka connections

#### 2. Application Security
- **API Keys**: Store in environment variables or secrets manager
- **Input Validation**: Validate all incoming lot data
- **Rate Limiting**: Implement rate limiting for health endpoints

#### 3. Monitoring & Alerting
- **Health Checks**: Monitor health endpoint availability
- **Log Monitoring**: Alert on ERROR level logs
- **Resource Monitoring**: Monitor CPU, memory, disk usage
- **Kafka Monitoring**: Monitor consumer lag and connection status

---

## Conclusion

The MokaMetrics.Simulator provides a comprehensive, production-ready simulation environment for coffee machine manufacturing processes. With its robust architecture, extensive configuration options, and thorough testing capabilities, it serves as an excellent foundation for production planning, system integration testing, and operator training.

For additional support or questions, refer to the troubleshooting section or contact the development team.

**Version**: 1.0.0
**Last Updated**: June 25, 2025
**Maintainer**: CoffeeMek S.p.A.
