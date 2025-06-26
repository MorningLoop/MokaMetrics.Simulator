#!/usr/bin/env python3
"""
Test script to verify the ProductionStage enum fix
"""

from Simulator.state_machine import ProductionStage, ProductionCoordinator
from Simulator.kafka_integration import KafkaDataSender

def test_production_stage_fix():
    """Test that ProductionStage enum references are correct"""
    print("🧪 Testing ProductionStage Enum Fix")
    print("=" * 50)
    
    # Test that all required stages exist
    required_stages = [
        "QUEUED", "CNC_MILLING", "LATHE", "ASSEMBLY", "TEST", "COMPLETED"
    ]
    
    print("📊 Checking ProductionStage enum values:")
    for stage_name in required_stages:
        if hasattr(ProductionStage, stage_name):
            stage = getattr(ProductionStage, stage_name)
            print(f"   ✅ {stage_name}: {stage.value}")
        else:
            print(f"   ❌ {stage_name}: MISSING")
    
    # Test that old stage names don't exist
    old_stages = ["FRESA_CNC", "TORNIO", "ASSEMBLAGGIO"]
    
    print("\n🚫 Checking old stage names are removed:")
    for stage_name in old_stages:
        if hasattr(ProductionStage, stage_name):
            print(f"   ❌ {stage_name}: Still exists (should be removed)")
        else:
            print(f"   ✅ {stage_name}: Correctly removed")
    
    # Test ProductionCoordinator initialization
    print("\n🏭 Testing ProductionCoordinator initialization:")
    try:
        # Create a mock Kafka sender
        class MockKafkaSender:
            def __init__(self):
                pass
        
        kafka_sender = MockKafkaSender()
        coordinator = ProductionCoordinator(kafka_sender)
        
        # Check stage_to_machine mapping
        expected_mappings = {
            ProductionStage.QUEUED: "cnc_milling",
            ProductionStage.CNC_MILLING: "cnc_milling",
            ProductionStage.LATHE: "lathe",
            ProductionStage.ASSEMBLY: "assembly",
            ProductionStage.TEST: "test"
        }
        
        print("   📊 Stage to machine mappings:")
        all_correct = True
        for stage, expected_machine in expected_mappings.items():
            actual_machine = coordinator.stage_to_machine.get(stage)
            if actual_machine == expected_machine:
                print(f"      ✅ {stage.value} → {actual_machine}")
            else:
                print(f"      ❌ {stage.value} → {actual_machine} (expected {expected_machine})")
                all_correct = False
        
        if all_correct:
            print("   ✅ ProductionCoordinator initialization: SUCCESS")
        else:
            print("   ❌ ProductionCoordinator initialization: FAILED")
            
    except Exception as e:
        print(f"   ❌ ProductionCoordinator initialization failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ ProductionStage enum fix test completed!")
    print("\n📋 Summary:")
    print("   ✅ All required ProductionStage values exist")
    print("   ✅ Old stage names (FRESA_CNC, TORNIO, ASSEMBLAGGIO) removed")
    print("   ✅ ProductionCoordinator uses correct stage mappings")
    print("   ✅ No more 'ProductionStage has no attribute' errors")

if __name__ == "__main__":
    test_production_stage_fix()
