#!/usr/bin/env python3
"""
Simple test script to verify the MokaMetrics.Simulator functionality
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import sys
import signal
import os
from pathlib import Path

class SimulatorTester:
    """Test the simulator functionality"""
    
    def __init__(self):
        self.simulator_process = None
        self.base_url = "http://localhost:8080"
        
    async def start_simulator(self):
        """Start the simulator in background"""
        print("🚀 Starting simulator...")
        
        # Start simulator process
        self.simulator_process = subprocess.Popen(
            [sys.executable, "-m", "Simulator.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path.cwd()
        )
        
        # Wait for startup
        await asyncio.sleep(5)
        
        if self.simulator_process.poll() is not None:
            stdout, stderr = self.simulator_process.communicate()
            print(f"❌ Simulator failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
        print("✅ Simulator started")
        return True
    
    def stop_simulator(self):
        """Stop the simulator"""
        if self.simulator_process:
            print("🛑 Stopping simulator...")
            self.simulator_process.terminate()
            try:
                self.simulator_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.simulator_process.kill()
            print("✅ Simulator stopped")
    
    async def test_health_check(self):
        """Test the health check endpoint"""
        print("🔍 Testing health check...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Health check passed: {data['status']}")
                        print(f"   Uptime: {data['uptime_seconds']:.1f}s")
                        print(f"   Kafka broker: {data['kafka_broker']}")
                        return True
                    else:
                        print(f"❌ Health check failed: HTTP {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_lot_sending(self):
        """Test sending lots using the test script"""
        print("📦 Testing lot sending...")
        
        try:
            # Run the test lot sender
            process = await asyncio.create_subprocess_exec(
                sys.executable, "test_lot_sender.py", 
                "--mode", "batch", "--count", "3",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ Test lots sent successfully")
                print(f"   Output: {stdout.decode().strip()}")
                return True
            else:
                print(f"❌ Failed to send test lots: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending test lots: {e}")
            return False
    
    async def run_tests(self):
        """Run all tests"""
        print("🧪 Starting MokaMetrics.Simulator Tests")
        print("=" * 50)
        
        # Check if virtual environment is activated
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("⚠️  Warning: Virtual environment may not be activated")
            print("   Run: source venv/bin/activate")
        
        # Start simulator
        if not await self.start_simulator():
            return False
        
        try:
            # Wait a bit more for full startup
            await asyncio.sleep(3)
            
            # Test health check
            health_ok = await self.test_health_check()
            
            if health_ok:
                # Test lot sending
                lots_ok = await self.test_lot_sending()
                
                # Wait a bit to see processing
                if lots_ok:
                    print("⏳ Waiting 10 seconds to observe processing...")
                    await asyncio.sleep(10)
                    
                    # Check health again
                    await self.test_health_check()
            
            print("\n" + "=" * 50)
            if health_ok and lots_ok:
                print("🎉 All tests passed! Simulator is working correctly.")
                print("\n📋 Next steps:")
                print("   1. Check simulator logs for processing details")
                print("   2. Send more lots: python test_lot_sender.py --mode continuous --rate 5")
                print("   3. Monitor health: curl http://localhost:8080/health")
            else:
                print("❌ Some tests failed. Check the output above for details.")
                
        finally:
            self.stop_simulator()

async def main():
    """Main test function"""
    tester = SimulatorTester()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Test interrupted by user")
        tester.stop_simulator()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())
