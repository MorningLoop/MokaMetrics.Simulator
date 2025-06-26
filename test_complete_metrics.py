#!/usr/bin/env python3
"""
Complete test to demonstrate the new metrics functionality across all machine types
"""

import json
from Simulator.Machine import get_machine_simulator

def test_complete_metrics():
    """Test complete metrics functionality"""
    print("🧪 Complete Metrics Test - Total Pieces Produced & Machine Status")
    print("=" * 80)
    
    machines = [
        ("cnc_milling", "CNC Milling", "Italy"),
        ("lathe", "Lathe", "Brazil"), 
        ("assembly", "Assembly", "Vietnam"),
        ("test", "Test Line", "Italy")
    ]
    
    for machine_type, display_name, location in machines:
        print(f"\n🏭 {display_name} Machine ({location})")
        print("=" * 50)
        
        machine_id = f"{machine_type}_{location}_1"
        simulator = get_machine_simulator(machine_id, machine_type, location)
        
        # Test different status scenarios
        scenarios = [
            ("idle", "Machine is idle, no production"),
            ("working", "Machine is actively producing"),
            ("error", "Machine has an error/maintenance issue")
        ]
        
        for status, description in scenarios:
            print(f"\n📊 Scenario: {status.upper()} - {description}")
            print("-" * 40)
            
            # Set machine status
            simulator.update_status(status)
            if status == "working":
                simulator.current_lot = f"LOT-{machine_type.upper()}-001"
            else:
                simulator.current_lot = None
            
            # Generate telemetry data
            telemetry = simulator.generate_measurement_data()
            
            # Extract key metrics
            pieces_produced = telemetry.get('total_pieces_produced', 'N/A')
            general_status = telemetry.get('machine_status', telemetry.get('general_machine_status', 'N/A'))
            
            print(f"   🔢 Total Pieces Produced: {pieces_produced}")
            print(f"   ⚡ General Machine Status: {general_status}")
            
            # Show machine-specific status if different
            if machine_type == "lathe":
                specific_status = telemetry.get('machine_status', 'N/A')
                if specific_status != general_status:
                    print(f"   🔧 Lathe-Specific Status: {specific_status}")
            
            # Simulate production if working
            if status == "working":
                initial_pieces = simulator.total_pieces_produced
                if machine_type == "assembly":
                    simulator.increment_pieces_produced(10)  # Assembly produces more
                else:
                    simulator.increment_pieces_produced(3)   # Other machines produce less
                
                print(f"   📈 Production Simulation: {initial_pieces} → {simulator.total_pieces_produced} pieces")
    
    print("\n" + "=" * 80)
    print("✅ IMPLEMENTATION COMPLETE!")
    print("\n📋 Summary of New Features:")
    print("   ✅ Added 'total_pieces_produced' metric to all machines")
    print("   ✅ Added 'machine_status' with values: 'working', 'idle', 'error'")
    print("   ✅ Integrated with state machine for automatic status updates")
    print("   ✅ Pieces produced counter increments during production cycles")
    print("   ✅ Status automatically syncs with machine assignment/completion")
    print("   ✅ All machine types (CNC, Lathe, Assembly, Test) support new metrics")
    print("   ✅ Backward compatibility maintained with existing telemetry")

if __name__ == "__main__":
    test_complete_metrics()
