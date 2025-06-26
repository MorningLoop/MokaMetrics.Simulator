# MokaMetrics.Simulator

🏭 **Coffee Machine Production Simulator** - A comprehensive Kafka-based production line simulator that processes coffee machine manufacturing lots through multiple production stages.

## 🚀 Quick Start

### 1. Setup Virtual Environment (Required)

```bash
# Create virtual environment (only once)
python3 -m venv venv

# Activate virtual environment (ALWAYS do this first!)
source venv/bin/activate  # On macOS/Linux
# OR on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Web Interface (Recommended)

```bash
# Make sure venv is activated first!
source venv/bin/activate

# Start web interface
python simulator_control.py web
```

Open `http://localhost:8081` in your browser for:
- ✅ Simulator control (start/stop)
- 📦 Manual lot creation
- 🚀 **Manual lot processing trigger**
- 📊 Real-time monitoring

### 3. Alternative: Console Interface

```bash
source venv/bin/activate
python simulator_control.py console
```

## 🔧 Troubleshooting

**If lots stay queued and don't process:**
1. Use the web interface at `http://localhost:8081`
2. Click **🚀 Start Processing Queued Lots** button

**Always activate virtual environment first:**
```bash
source venv/bin/activate  # Check that (venv) appears in your prompt
```

## 📖 Documentation

- [Complete Usage Guide](USAGE_GUIDE.md) - Detailed setup and usage
- [Kafka Topics Documentation](kafka-topics-doc.md) - Message formats and topics
- [Testing Mode Guide](TESTING_MODE_GUIDE.md) - Accelerated testing features

## 🏭 Production Flow

```
Kafka Input → Queue → CNC → Lathe → Assembly → Testing → Complete
```

Processes coffee machine lots through 4 manufacturing stages with realistic telemetry data generation.

## ⚡ Features

- **Accelerated Testing Mode** - 1-2 minute processing per stage (vs real 30-45 minutes)
- **Multi-location Support** - Italy, Brazil, Vietnam manufacturing sites
- **Real-time Telemetry** - High-frequency data generation (1-second intervals)
- **Web-based Control** - Modern interface for monitoring and control
- **Kafka Integration** - Production-ready messaging with topic documentation
- **Machine Simulation** - Realistic CNC, Lathe, Assembly, and Test machine behavior