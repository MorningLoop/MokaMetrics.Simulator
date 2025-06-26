# 🧪 MokaMetrics Simulator - Testing Mode Guide

## 🎯 Overview

The MokaMetrics Simulator has been enhanced with **Testing Mode** features for rapid development, testing, and demonstration purposes. This mode provides accelerated processing, high-frequency telemetry, and comprehensive monitoring capabilities.

## ✨ Key Features

### 🚀 **Accelerated Processing**
- **Total cycle time**: ~5 minutes (vs. 2-4 hours in production mode)
- **Per-stage timing**: 1-2 minutes each (CNC → Lathe → Assembly → Testing)
- **Maintains realistic proportions** between different machine types
- **Perfect for demos and testing** without long wait times

### ⚡ **High-Frequency Telemetry**
- **1-second intervals**: Telemetry sent every second while machines are processing
- **Real-time data flow**: Continuous stream to all `mokametrics.telemetry.*` topics
- **Production-like volume**: Simulates high-throughput manufacturing environments
- **Specification compliant**: All messages match `kafka-topics-doc.md` exactly

### 📊 **Real-Time Monitoring**
- **Live statistics**: Messages/second, machine utilization, queue status
- **Active lot tracking**: Current stage, processing times, customer info
- **Performance metrics**: Cycle times, completion rates, efficiency
- **Topic monitoring**: Message counts per Kafka topic

### 🎮 **Dual Control Interfaces**

#### **Console Interface** (Rich Terminal UI)
```bash
python simulator_control.py console
```
- **Beautiful terminal dashboard** with live updates
- **Real-time statistics** refreshed every 0.5 seconds
- **Machine status visualization** with color coding
- **Keyboard controls**: Ctrl+C to stop, A to add lot

#### **Web Interface** (Browser Dashboard)
```bash
python simulator_control.py web
```
- **Browser-based control panel** at `http://localhost:8081`
- **WebSocket real-time updates** every second
- **Start/stop simulator controls** via web buttons
- **📦 Add New Lot form** with validation
- **Mobile-responsive design** for any device
- **Remote monitoring capability**

### 📦 **Manual Lot Addition**
- **Web form**: Easy point-and-click lot creation
- **Command-line tool**: Batch lot generation for testing
- **REST API**: Integration with external systems
- **Interactive console**: Add lots during monitoring
- **Validation**: Automatic data validation and error handling

## 🚀 Quick Start

### 1. **Install Dependencies**
```bash
pip install rich aiohttp-cors
```

### 2. **Choose Your Interface**

#### **Console Interface** (Recommended for Development)
```bash
python simulator_control.py console
```

#### **Web Interface** (Recommended for Demos)
```bash
python simulator_control.py web
# Open http://localhost:8081 in your browser
```

#### **Custom Web Port**
```bash
python simulator_control.py web --port 8080
```

### 3. **Add Test Lots**

#### **Web Interface** (Easiest)
- Use the "📦 Add New Lot" form in the web interface
- Fill in customer, quantity, location, and priority
- Click "Add Lot" button

#### **Command Line** (Fastest for Testing)
```bash
# Add single lot
python add_lot.py --customer "Lavazza" --quantity 150 --location "Italia"

# Add multiple lots for testing
python add_lot.py --batch 5

# Add lots with specific parameters
python add_lot.py --batch 3 --location "Brasile" --priority "high"
```

#### **API Call** (For Integration)
```bash
curl -X POST http://localhost:8081/api/add_lot \
     -H 'Content-Type: application/json' \
     -d '{"customer":"Test Customer","quantity":100,"location":"Italia"}'
```

## 📡 Kafka Topics

### **Telemetry Topics** (High-Frequency)
- `mokametrics.telemetry.cnc` - CNC machine data
- `mokametrics.telemetry.lathe` - Lathe machine data  
- `mokametrics.telemetry.assembly` - Assembly line data
- `mokametrics.telemetry.testing` - Test line data

### **Production Completion Topic**
- `mokametrics.production.lotto_completato` - Lot completion summaries

### **Message Frequency**
- **Telemetry**: 1 message/second per active machine
- **Completion**: 1 message per completed lot (~every 5 minutes)
- **Total volume**: ~20-50 messages/second during active processing

## 📊 Monitoring Capabilities

### **System Statistics**
- Uptime and total runtime
- Total lots completed
- Total messages sent
- Messages per second/minute
- Average cycle time

### **Active Lot Tracking**
- Current lots in production
- Stage progression (Queued → CNC → Lathe → Assembly → Testing → Completed)
- Processing times per stage
- Customer and quantity information

### **Machine Utilization**
- Real-time busy/idle status
- Utilization percentage over time
- Current lot assignments
- Total processing time per machine

### **Queue Status**
- Lots waiting at each stage
- Queue lengths and priorities
- Processing bottlenecks identification

## 🔧 Configuration

### **Processing Times** (Accelerated)
```yaml
# All stages: 1-2 minutes (60-120 seconds)
fresa_cnc: 60-120s      # vs. 20-60 minutes in production
tornio: 60-120s         # vs. 15-45 minutes in production  
assemblaggio: 60-120s   # vs. 30-90 minutes in production
test: 60-120s           # vs. 10-30 minutes in production
```

### **Telemetry Frequency**
```yaml
telemetry_interval: 1.0  # Send every 1 second
telemetry_enabled: true  # High-frequency mode enabled
```

### **Interface Ports**
```yaml
console: N/A             # Terminal-based
web: 8081               # Default web port
health_check: 8080      # Health endpoint (unchanged)
```

## 🧪 Testing Scenarios

### **1. Basic Functionality Test**
```bash
# Start simulator
python simulator_control.py console

# Send test lots (in another terminal)
python test_lot_sender.py --mode batch --count 3

# Observe: Lots should complete in ~5 minutes each
```

### **2. High-Volume Test**
```bash
# Start web interface
python simulator_control.py web

# Send many lots
python test_lot_sender.py --mode batch --count 20

# Monitor: Web dashboard should show high message rates
```

### **3. Specification Compliance Test**
```bash
# Run comprehensive test
python test_specification_compliance.py

# Verify: All messages match kafka-topics-doc.md format
```

### **4. Performance Test**
```bash
# Run accelerated simulator test
python test_accelerated_simulator.py

# Verify: All features working correctly
```

## 📈 Expected Performance

### **Timing Expectations**
- **Lot completion**: 4-8 minutes per lot
- **Stage transitions**: 1-2 minutes per stage
- **Queue processing**: Near real-time
- **Telemetry frequency**: 1 message/second per active machine

### **Message Volume**
- **Low activity**: 5-10 messages/second
- **Medium activity**: 20-30 messages/second  
- **High activity**: 40-60 messages/second
- **Peak bursts**: Up to 100 messages/second

### **Resource Usage**
- **CPU**: Low to moderate (monitoring overhead)
- **Memory**: ~50-100MB (message buffering)
- **Network**: ~1-5 KB/second (Kafka traffic)

## 🔍 Troubleshooting

### **Common Issues**

#### **"Rich library not available"**
```bash
pip install rich
```

#### **"aiohttp-cors not found"**
```bash
pip install aiohttp-cors
```

#### **Web interface not accessible**
- Check firewall settings
- Try `--host 127.0.0.1` for localhost only
- Verify port not in use: `lsof -i :8081`

#### **Kafka connection errors**
- Verify Kafka broker: `165.227.168.240:9093`
- Check network connectivity
- Review Kafka logs

#### **No telemetry data**
- Ensure lots are being processed
- Check machine assignments
- Verify high-frequency telemetry enabled

### **Debug Commands**
```bash
# Test Kafka connectivity
python -c "from Simulator.kafka_integration import KafkaDataSender; import asyncio; asyncio.run(KafkaDataSender({}).start())"

# Test monitoring system
python -c "from Simulator.monitoring import monitor; monitor.start(); print(monitor.get_current_stats())"

# Test machine simulators
python -c "from Simulator.Machine import get_machine_simulator; print(get_machine_simulator('test', 'fresa_cnc', 'Italia').generate_measurement_data())"
```

## 🎯 Use Cases

### **Development**
- **Rapid iteration**: Test changes without waiting hours
- **Integration testing**: Verify Kafka topic structure
- **Performance testing**: Measure system throughput

### **Demonstrations**
- **Live demos**: Show complete cycles in minutes
- **Client presentations**: Real-time dashboard visualization
- **Training**: Hands-on experience with realistic data

### **Testing**
- **Load testing**: High-frequency message generation
- **Stress testing**: Multiple concurrent lots
- **Compliance testing**: Verify specification adherence

## 🔄 Switching Back to Production Mode

To return to production timing:

1. **Restore processing times** in machine simulators
2. **Disable high-frequency telemetry** (set interval to 60+ seconds)
3. **Update configuration** files
4. **Restart simulator** with production settings

## 📞 Support

For issues or questions:
1. Check this guide first
2. Run test scripts to verify setup
3. Review Kafka broker connectivity
4. Check system logs for errors

---

**🎉 Happy Testing!** The accelerated simulator is designed to make development and testing faster and more enjoyable while maintaining full production compatibility.
