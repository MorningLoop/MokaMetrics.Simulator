#!/usr/bin/env python3
"""
Test script to verify the status enum mapping works correctly
"""

from Simulator.Machine import get_machine_simulator
from Simulator.models import MachineStatuses

def test_status_enum_mapping():
    """Test that internal status strings map correctly to Kafka status integers"""
    print("🧪 Testing Status Enum Mapping")
    print("=" * 50)
    
    # Create a test machine
    simulator = get_machine_simulator("cnc_Italy_1", "cnc_milling", "Italy")
    
    # Test status mappings
    status_tests = [
        ("idle", MachineStatuses.IDLE.value, "Machine is idle"),
        ("working", MachineStatuses.OPERATIONAL.value, "Machine is working"),
        ("error", MachineStatuses.ALARM.value, "Machine has an error")
    ]
    
    print("\n📊 Status Mapping Tests:")
    print("-" * 30)
    
    for internal_status, expected_kafka_status, description in status_tests:
        # Set internal status
        simulator.update_status(internal_status)
        
        # Get Kafka status
        kafka_status = simulator.get_kafka_status()
        
        # Verify mapping
        if kafka_status == expected_kafka_status:
            print(f"   ✅ '{internal_status}' → {kafka_status} ({description})")
        else:
            print(f"   ❌ '{internal_status}' → {kafka_status} (expected {expected_kafka_status})")
    
    print("\n📋 MachineStatuses Enum Values:")
    print("-" * 30)
    for status in MachineStatuses:
        print(f"   {status.value}: {status.name}")
    
    print("\n🔄 Testing with Telemetry Data:")
    print("-" * 30)
    
    for internal_status, expected_kafka_status, description in status_tests:
        simulator.update_status(internal_status)
        if internal_status == "working":
            simulator.current_lot = "TEST-LOT-001"
        else:
            simulator.current_lot = None
        
        # Generate telemetry
        telemetry = simulator.generate_measurement_data()
        actual_status = telemetry.get("status", "MISSING")
        
        print(f"   Status '{internal_status}': telemetry.status = {actual_status}")
    
    print("\n" + "=" * 50)
    print("✅ Status enum mapping test completed!")

if __name__ == "__main__":
    test_status_enum_mapping()
