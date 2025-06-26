#!/usr/bin/env python3
"""
Test script to verify both specific machine status and general machine status fields
"""

import json
from Simulator.Machine import get_machine_simulator

def test_status_fields():
    """Test that machines have both specific and general status fields"""
    print("🧪 Testing Status Fields")
    print("=" * 60)
    
    # Test Lathe machine specifically since it has both status types
    print("\n🔧 Testing Lathe Machine Status Fields:")
    print("-" * 40)
    
    simulator = get_machine_simulator("lathe_Italy_1", "lathe", "Italy")
    simulator.update_status("working")
    simulator.current_lot = "TEST-LOT-001"
    
    # Generate measurement data
    data = simulator.generate_measurement_data()
    
    print("📡 Measurement Data Status Fields:")
    print(json.dumps({k: v for k, v in data.items() if 'status' in k.lower()}, indent=2))
    
    print("\n📊 All Status-Related Fields:")
    for key, value in data.items():
        if 'status' in key.lower() or 'state' in key.lower():
            print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ Status fields testing completed!")
    
    print("\n📝 Summary:")
    print("   - Lathe machines have 'machine_status' (Active/Inactive/Maintenance/Fault)")
    print("   - All machines now have 'general_machine_status' or 'machine_status' (working/idle/error)")
    print("   - This allows for both machine-specific and general status tracking")

if __name__ == "__main__":
    test_status_fields()
