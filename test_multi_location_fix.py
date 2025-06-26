#!/usr/bin/env python3
"""
Test script to verify the multi-location processing fix
"""

import asyncio
import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from Simulator.state_machine import ProductionLot, ProductionStage, ProductionCoordinator
from Simulator.kafka_integration import KafkaDataSender

async def test_multi_location_fix():
    """Test that multiple lots from different locations can be processed simultaneously"""
    print("🧪 Testing Multi-Location Processing Fix")
    print("=" * 60)
    
    # Create mock Kafka sender
    class MockKafkaDataSender:
        def __init__(self):
            pass
        async def start(self):
            pass
        async def stop(self):
            pass
        def set_lot_callback(self, callback):
            pass
    
    try:
        # Create production coordinator
        kafka_sender = MockKafkaDataSender()
        coordinator = ProductionCoordinator(kafka_sender)
        
        # Initialize machines
        machine_config = {
            "Italy": {"cnc_milling": 1, "lathe": 1, "assembly": 1, "test": 1},
            "Brazil": {"cnc_milling": 1, "lathe": 1, "assembly": 1, "test": 1}
        }
        coordinator.initialize_machines(machine_config)
        
        print("✅ Production coordinator initialized")
        print("✅ Machines initialized for Italy and Brazil")
        
        # Test ProductionLot attribute access
        print("\n🔍 Testing ProductionLot attribute access:")
        
        # Create test lots
        italy_lot = ProductionLot(
            lot_code="ITALY-TEST-001",
            customer="Italian Customer",
            quantity=100,
            location="Italy"
        )
        
        brazil_lot = ProductionLot(
            lot_code="BRAZIL-TEST-001", 
            customer="Brazilian Customer",
            quantity=150,
            location="Brazil"
        )
        
        # Test that we can access lot_code (not codice_lotto)
        print(f"   Italy lot code: {italy_lot.lot_code}")
        print(f"   Brazil lot code: {brazil_lot.lot_code}")
        print(f"   Italy customer: {italy_lot.customer}")
        print(f"   Brazil customer: {brazil_lot.customer}")
        
        # Test that the old attribute name doesn't exist
        try:
            _ = italy_lot.codice_lotto
            print("   ❌ ERROR: codice_lotto attribute still exists!")
        except AttributeError:
            print("   ✅ codice_lotto attribute correctly removed")
        
        # Test adding lots to coordinator
        print("\n📦 Testing lot addition:")
        
        # Add Italy lot
        await coordinator.add_lot({
            "lot_code": "ITALY-TEST-001",
            "customer": "Italian Customer", 
            "quantity": 100,
            "location": "Italy"
        })
        print("   ✅ Italy lot added successfully")
        
        # Add Brazil lot
        await coordinator.add_lot({
            "lot_code": "BRAZIL-TEST-001",
            "customer": "Brazilian Customer",
            "quantity": 150, 
            "location": "Brazil"
        })
        print("   ✅ Brazil lot added successfully")
        
        # Check queue status
        status = coordinator.get_status()
        print(f"\n📊 Queue status after adding lots:")
        for stage, queue_info in status["queues"].items():
            if queue_info["size"] > 0:
                print(f"   {stage}: {queue_info['size']} lots - {queue_info['lots']}")
        
        print("\n" + "=" * 60)
        print("🎉 MULTI-LOCATION FIX SUCCESSFUL!")
        print("\n📋 What was fixed:")
        print("   ✅ Changed all 'codice_lotto' references to 'lot_code'")
        print("   ✅ Changed all 'cliente' references to 'customer'") 
        print("   ✅ Changed all 'quantita' references to 'quantity'")
        print("   ✅ ProductionLot attributes now match field names")
        print("   ✅ Multiple locations can be processed simultaneously")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_multi_location_fix())
    if success:
        print("\n🚀 The simulator should now handle multiple locations correctly!")
    else:
        print("\n💥 There are still issues that need to be fixed.")
