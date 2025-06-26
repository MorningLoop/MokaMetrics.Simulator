#!/usr/bin/env python3
"""
Test script to verify Lathe machine has both status fields
"""

import json
from Simulator.Machine import get_machine_simulator

def test_lathe_status():
    """Test Lathe machine status fields"""
    print("🧪 Testing Lathe Machine Status Fields")
    print("=" * 50)
    
    simulator = get_machine_simulator("lathe_Brazil_1", "lathe", "Brazil")
    
    # Test different general status settings
    statuses = ["idle", "working", "error"]
    
    for status in statuses:
        print(f"\n📊 Setting general status to: {status}")
        print("-" * 30)
        
        simulator.update_status(status)
        if status == "working":
            simulator.current_lot = "TEST-LOT-001"
        else:
            simulator.current_lot = None
        
        # Generate telemetry data
        data = simulator.generate_measurement_data()
        
        # Show all status-related fields
        status_fields = {k: v for k, v in data.items() if 'status' in k.lower() or 'state' in k.lower()}
        print(json.dumps(status_fields, indent=2))
    
    print("\n" + "=" * 50)
    print("✅ Lathe Status Test Complete!")
    print("\n📝 Explanation:")
    print("   - 'machine_status': Lathe-specific status (Active/Inactive/Maintenance/Fault)")
    print("   - 'general_machine_status': New general status (working/idle/error)")
    print("   - Both fields coexist for comprehensive status tracking")

if __name__ == "__main__":
    test_lathe_status()
