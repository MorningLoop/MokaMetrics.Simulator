#!/usr/bin/env python3
"""
Test script to verify the new metrics (total_pieces_produced and machine_status) are working correctly
"""

import asyncio
import json
from Simulator.Machine import get_machine_simulator
from Simulator.models import Location

async def test_new_metrics():
    """Test the new metrics functionality"""
    print("🧪 Testing new metrics: total_pieces_produced and machine_status")
    print("=" * 60)
    
    # Test each machine type
    machine_types = [
        ("cnc_milling", "CNC Milling"),
        ("lathe", "Lathe"),
        ("assembly", "Assembly"),
        ("test", "Test")
    ]
    
    for machine_type, display_name in machine_types:
        print(f"\n🔧 Testing {display_name} Machine:")
        print("-" * 40)
        
        # Create machine simulator
        machine_id = f"{machine_type}_Italy_1"
        simulator = get_machine_simulator(machine_id, machine_type, "Italy")
        
        if not simulator:
            print(f"❌ Failed to create {display_name} simulator")
            continue
        
        print(f"✅ Created {display_name} simulator: {machine_id}")
        
        # Test initial state
        print(f"📊 Initial pieces produced: {simulator.total_pieces_produced}")
        print(f"📊 Initial status: {simulator.current_status}")
        
        # Test status changes
        print("\n🔄 Testing status changes:")
        simulator.update_status("working")
        print(f"   Status set to 'working': {simulator.current_status}")
        
        simulator.update_status("idle")
        print(f"   Status set to 'idle': {simulator.current_status}")
        
        simulator.update_status("error")
        print(f"   Status set to 'error': {simulator.current_status}")
        
        # Test pieces produced increment
        print("\n📈 Testing pieces produced increment:")
        initial_pieces = simulator.total_pieces_produced
        simulator.increment_pieces_produced(5)
        print(f"   Added 5 pieces: {initial_pieces} → {simulator.total_pieces_produced}")
        
        # Test telemetry data generation
        print("\n📡 Testing telemetry data generation:")
        
        # Set machine to working status for realistic data
        simulator.update_status("working")
        simulator.current_lot = "TEST-LOT-001"
        
        try:
            # Test generate_data method
            data = simulator.generate_data()
            print(f"   ✅ generate_data() successful")
            print(f"   📊 Contains total_pieces_produced: {'total_pieces_produced' in data}")
            print(f"   📊 Contains machine_status: {'machine_status' in data}")
            if 'total_pieces_produced' in data:
                print(f"   📊 Total pieces: {data['total_pieces_produced']}")
            if 'machine_status' in data:
                print(f"   📊 Machine status: {data['machine_status']}")
            
        except Exception as e:
            print(f"   ❌ generate_data() failed: {e}")
        
        try:
            # Test generate_measurement_data method
            measurement_data = simulator.generate_measurement_data()
            print(f"   ✅ generate_measurement_data() successful")
            print(f"   📊 Contains total_pieces_produced: {'total_pieces_produced' in measurement_data}")
            print(f"   📊 Contains machine_status: {'machine_status' in measurement_data or 'general_machine_status' in measurement_data}")
            if 'total_pieces_produced' in measurement_data:
                print(f"   📊 Total pieces: {measurement_data['total_pieces_produced']}")
            if 'machine_status' in measurement_data:
                print(f"   📊 Machine status: {measurement_data['machine_status']}")
            elif 'general_machine_status' in measurement_data:
                print(f"   📊 Machine status: {measurement_data['general_machine_status']}")
            
        except Exception as e:
            print(f"   ❌ generate_measurement_data() failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ New metrics testing completed!")

if __name__ == "__main__":
    asyncio.run(test_new_metrics())
