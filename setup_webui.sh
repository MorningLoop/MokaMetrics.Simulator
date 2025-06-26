#!/bin/bash
# Setup script for MokaMetrics Simulator Web UI

echo "🏭 MokaMetrics Simulator - Web UI Setup"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "simulator_control.py" ]; then
    echo "❌ Error: Please run this script from the MokaMetrics.Simulator directory"
    echo "Expected to find simulator_control.py in current directory"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo ""

# Create virtual environment
echo "🐍 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    echo "Make sure Python 3 is installed: python3 --version"
    exit 1
fi

echo "✅ Virtual environment created"

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
echo "This may take a few minutes..."

# Install core dependencies first
pip install aiokafka aiohttp pytz

# Install interface dependencies
pip install rich aiohttp-cors

# Install from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    echo "📋 Installing from requirements.txt..."
    pip install -r requirements.txt
fi

# Verify installation
echo "🔍 Verifying installation..."
python -c "
import sys
try:
    import aiokafka
    import aiohttp
    import rich
    import pytz
    print('✅ All core dependencies installed successfully')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Dependency verification failed"
    exit 1
fi

# Test the simulator control script
echo "🧪 Testing simulator control script..."
python simulator_control.py --help > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Simulator control script test failed"
    exit 1
fi

echo "✅ Simulator control script working"

# Create activation script
echo "📝 Creating activation script..."
cat > activate_webui.sh << 'EOF'
#!/bin/bash
# Activation script for MokaMetrics Simulator Web UI

echo "🔌 Activating MokaMetrics Simulator environment..."
source venv/bin/activate

echo "✅ Environment activated!"
echo ""
echo "Available commands:"
echo "  python simulator_control.py web              # Start web interface"
echo "  python simulator_control.py console          # Start console interface"
echo "  python simulator_control.py web --port 8080  # Custom port"
echo ""
echo "Web interface will be available at: http://localhost:8081"
echo "Press Ctrl+C to stop the simulator"
EOF

chmod +x activate_webui.sh

# Create quick start script
echo "📝 Creating quick start script..."
cat > start_webui.sh << 'EOF'
#!/bin/bash
# Quick start script for Web UI

echo "🚀 Starting MokaMetrics Simulator Web UI..."
source venv/bin/activate
python simulator_control.py web
EOF

chmod +x start_webui.sh

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📋 What was installed:"
echo "  ✅ Python virtual environment (venv/)"
echo "  ✅ All required dependencies"
echo "  ✅ Rich terminal library for console interface"
echo "  ✅ aiohttp and aiohttp-cors for web interface"
echo "  ✅ aiokafka for Kafka integration"
echo ""
echo "🚀 How to start:"
echo ""
echo "Option 1 - Quick start:"
echo "  ./start_webui.sh"
echo ""
echo "Option 2 - Manual activation:"
echo "  source venv/bin/activate"
echo "  python simulator_control.py web"
echo ""
echo "Option 3 - Use activation helper:"
echo "  ./activate_webui.sh"
echo "  python simulator_control.py web"
echo ""
echo "🌐 Web interface will be available at:"
echo "  http://localhost:8081"
echo ""
echo "🎮 Alternative console interface:"
echo "  python simulator_control.py console"
echo ""
echo "📚 For more information, see TESTING_MODE_GUIDE.md"
echo ""
echo "Happy testing! 🧪"
