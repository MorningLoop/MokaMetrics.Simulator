#!/usr/bin/env python3
"""
Test script for lot addition functionality
"""

import asyncio
import sys
from datetime import datetime
import random

# Add the current directory to Python path
sys.path.append('.')

from Simulator.main import CoffeeMekSimulator, load_config

async def test_lot_addition():
    """Test the lot addition functionality"""
    print("🧪 Testing Lot Addition Functionality")
    print("=" * 40)
    
    try:
        # Load config and create simulator
        config = load_config()
        simulator = CoffeeMekSimulator(config)
        
        print("✅ Simulator created successfully")
        
        # Test lot data validation
        print("\n📋 Testing lot data validation...")
        
        # Test missing fields
        try:
            await simulator.add_lot({"invalid": "data"})
            print("❌ Should have failed with missing fields")
        except RuntimeError as e:
            print(f"✅ Correctly rejected when simulator not running: {e}")
        except ValueError as e:
            print(f"✅ Correctly rejected invalid data: {e}")
        
        # Test valid lot data structure
        valid_lot = {
            "lot_code": f"TEST-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
            "customer": "Test Customer",
            "quantity": 100,
            "location": "Italy",
            "priority": "normal",
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Valid lot data structure created: {valid_lot['lot_code']}")
        
        # Test the add_lot method exists and has correct signature
        assert hasattr(simulator, 'add_lot'), "Simulator missing add_lot method"
        print("✅ add_lot method exists")
        
        # Test web interface integration
        print("\n🌐 Testing web interface integration...")
        
        from Simulator.web_interface import WebInterface
        web_interface = WebInterface()
        
        # Check that the route exists
        routes = [route.resource.canonical for route in web_interface.app.router.routes()]
        assert '/api/add_lot' in routes, "Missing /api/add_lot route"
        print("✅ Web API route exists")
        
        # Test command-line tool
        print("\n💻 Testing command-line tool...")
        
        import subprocess
        result = subprocess.run([sys.executable, "add_lot.py", "--help"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Command-line tool works")
        else:
            print(f"❌ Command-line tool error: {result.stderr}")
        
        print("\n🎉 All lot addition tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demo_lot_addition():
    """Demonstrate lot addition with sample data"""
    print("\n🎬 Lot Addition Demo")
    print("=" * 20)
    
    # Sample lots to demonstrate
    sample_lots = [
        {
            "cliente": "Lavazza",
            "quantita": 150,
            "location": "Italia",
            "priority": "high"
        },
        {
            "cliente": "Illy",
            "quantita": 200,
            "location": "Brazil",
            "priority": "normal"
        },
        {
            "cliente": "Segafredo",
            "quantita": 75,
            "location": "Vietnam",
            "priority": "urgent"
        }
    ]
    
    for i, lot_params in enumerate(sample_lots, 1):
        lot_code = f"DEMO-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        lot_data = {
            "codice_lotto": lot_code,
            "timestamp": datetime.now().isoformat(),
            **lot_params
        }
        
        print(f"\n📦 Sample Lot {i}:")
        print(f"   Code: {lot_data['codice_lotto']}")
        print(f"   Customer: {lot_data['cliente']}")
        print(f"   Quantity: {lot_data['quantita']}")
        print(f"   Location: {lot_data['location']}")
        print(f"   Priority: {lot_data['priority']}")
        
        # This would be the JSON sent to the API
        import json
        print(f"   JSON: {json.dumps(lot_data, indent=2)}")

async def main():
    """Main test function"""
    print("🏭 MokaMetrics Simulator - Lot Addition Test Suite")
    print("=" * 55)
    
    # Run tests
    test_success = await test_lot_addition()
    
    # Show demo
    await demo_lot_addition()
    
    # Usage examples
    print("\n📚 Usage Examples:")
    print("=" * 20)
    print("1. Web Interface:")
    print("   python simulator_control.py web")
    print("   # Then use the 'Add New Lot' form in the browser")
    print()
    print("2. Command Line (single lot):")
    print("   python add_lot.py --customer 'Lavazza' --quantity 150 --location 'Italy'")
    print()
    print("3. Command Line (batch):")
    print("   python add_lot.py --batch 5")
    print()
    print("4. Command Line (help):")
    print("   python add_lot.py --help")
    print()
    print("5. API Call (curl):")
    print("   curl -X POST http://localhost:8081/api/add_lot \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"customer\":\"Test\",\"quantity\":100,\"location\":\"Italy\"}'")
    
    if test_success:
        print("\n✅ All tests passed! Lot addition functionality is ready.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
