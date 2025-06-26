#!/usr/bin/env python3
"""
Simple web UI starter that bypasses import issues
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def start_web_interface():
    """Start the web interface with minimal imports"""
    print("🏭 MokaMetrics Simulator - Web Interface")
    print("=" * 45)
    
    try:
        # Test basic imports first
        print("📦 Checking dependencies...")
        
        try:
            import aiohttp
            print("✅ aiohttp available")
        except ImportError:
            print("❌ aiohttp not found. Install with: pip install aiohttp")
            return False
        
        try:
            import aiohttp_cors
            print("✅ aiohttp-cors available")
        except ImportError:
            print("⚠️  aiohttp-cors not found (optional, using basic CORS)")
        
        # Import web interface
        print("🌐 Loading web interface...")
        from Simulator.web_interface import WebInterface
        print("✅ Web interface loaded")
        
        # Start server
        print("🚀 Starting web server...")
        interface = WebInterface(host="0.0.0.0", port=8081)
        runner = await interface.start_server()
        
        print("\n" + "=" * 50)
        print("🎉 Web Interface Started Successfully!")
        print("=" * 50)
        print(f"🌐 Access at: http://localhost:8081")
        print("📱 Mobile friendly interface")
        print("🎮 Start/stop simulator controls")
        print("📦 Add lots manually")
        print("📊 Real-time monitoring")
        print("\nPress Ctrl+C to stop")
        print("=" * 50)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            await interface.stop_server(runner)
            print("✅ Shutdown complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    try:
        success = asyncio.run(start_web_interface())
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
