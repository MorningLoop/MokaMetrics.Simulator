#!/usr/bin/env python3
"""
Test script for the accelerated MokaMetrics Simulator
Tests all new features: accelerated processing, high-frequency telemetry, and monitoring
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta

# Add the Simulator module to the path
sys.path.append('.')

from Simulator.main import CoffeeMekSimulator, load_config
from Simulator.monitoring import monitor
from Simulator.kafka_integration import KafkaDataSender

class AcceleratedSimulatorTest:
    """Test the accelerated simulator functionality"""
    
    def __init__(self):
        self.config = load_config()
        self.simulator = None
        self.test_results = {}
    
    async def test_accelerated_processing_times(self):
        """Test that processing times are accelerated"""
        print("\n🚀 Testing accelerated processing times...")
        
        from Simulator.Machine import get_machine_simulator
        
        # Test each machine type
        machines = [
            ("fresa_cnc", "Italia"),
            ("tornio", "Brasile"),
            ("assemblaggio", "Vietnam"),
            ("test", "Italia")
        ]
        
        for machine_type, location in machines:
            simulator = get_machine_simulator(f"{machine_type}_{location}_1", machine_type, location)
            if simulator:
                processing_time = simulator.get_processing_time()
                # Should be between 60-120 seconds (1-2 minutes)
                assert 60 <= processing_time <= 120, f"{machine_type} processing time {processing_time}s not in range 60-120s"
                print(f"✅ {machine_type}: {processing_time}s (accelerated)")
        
        self.test_results["accelerated_processing"] = True
        print("✅ All processing times are accelerated correctly")
    
    async def test_monitoring_system(self):
        """Test the monitoring system"""
        print("\n📊 Testing monitoring system...")
        
        # Test basic monitoring functionality
        monitor.start()
        
        # Record some test data
        monitor.record_message_sent("mokametrics.telemetry.cnc", "test-key")
        monitor.update_machine_status("cnc_Italy_1", "fresa_cnc", "Italy", True, "TEST-001")
        monitor.update_lot_status("TEST-001", "Test Customer", 100, "Italy", "cnc")
        
        # Get stats
        stats = monitor.get_current_stats()
        
        # Verify stats structure
        required_fields = [
            "timestamp", "uptime_seconds", "total_lots_completed",
            "total_messages_sent", "topic_stats", "active_lots",
            "machine_utilization", "queue_status"
        ]
        
        for field in required_fields:
            assert field in stats, f"Missing field in stats: {field}"
        
        # Verify message was recorded
        assert stats["total_messages_sent"] >= 1, "Message sending not recorded"
        assert "mokametrics.telemetry.cnc" in stats["topic_stats"], "Topic stats not recorded"
        
        # Verify machine status was recorded
        assert len(stats["machine_utilization"]) >= 1, "Machine utilization not recorded"
        
        # Verify lot status was recorded
        assert len(stats["active_lots"]) >= 1, "Active lots not recorded"
        
        await monitor.stop()
        self.test_results["monitoring_system"] = True
        print("✅ Monitoring system working correctly")
    
    async def test_specification_compliance(self):
        """Test that messages still comply with specification"""
        print("\n📋 Testing specification compliance...")
        
        from Simulator.Machine import get_machine_simulator
        
        # Test CNC telemetry compliance
        cnc_simulator = get_machine_simulator("cnc_Italy_1", "fresa_cnc", "Italia")
        if cnc_simulator:
            cnc_simulator.current_lot = "SPEC-TEST-001"
            telemetry_data = cnc_simulator.generate_measurement_data()
            
            # Verify required fields for CNC telemetry
            required_fields = [
                "lot_code", "cycle_time", "cutting_depth", "vibration",
                "tool_alarms", "local_timestamp", "utc_timestamp", "site", "machine_id"
            ]
            
            for field in required_fields:
                assert field in telemetry_data, f"Missing CNC field: {field}"
            
            # Verify field types
            assert isinstance(telemetry_data["cycle_time"], (int, float))
            assert isinstance(telemetry_data["cutting_depth"], (int, float))
            assert isinstance(telemetry_data["vibration"], (int, float))
            assert telemetry_data["site"] in ["Italy", "Brazil", "Vietnam"]
            
            print("✅ CNC telemetry complies with specification")
        
        # Test Lathe telemetry compliance
        lathe_simulator = get_machine_simulator("lathe_Brazil_1", "tornio", "Brasile")
        if lathe_simulator:
            lathe_simulator.current_lot = "SPEC-TEST-002"
            telemetry_data = lathe_simulator.generate_measurement_data()
            
            # Verify required fields for Lathe telemetry
            required_fields = [
                "lot_code", "machine_status", "rotation_speed", "spindle_temperature",
                "completed_pieces", "local_timestamp", "utc_timestamp", "site", "machine_id"
            ]
            
            for field in required_fields:
                assert field in telemetry_data, f"Missing Lathe field: {field}"
            
            # Verify field types and values
            assert telemetry_data["machine_status"] in ["Active", "Inactive", "Maintenance", "Fault"]
            assert isinstance(telemetry_data["rotation_speed"], (int, float))
            assert isinstance(telemetry_data["completed_pieces"], int)
            
            print("✅ Lathe telemetry complies with specification")
        
        self.test_results["specification_compliance"] = True
        print("✅ All telemetry data complies with specification")
    
    async def test_kafka_integration(self):
        """Test Kafka integration with monitoring"""
        print("\n📡 Testing Kafka integration...")
        
        kafka_sender = KafkaDataSender(self.config)
        await kafka_sender.start()
        
        # Test telemetry sending
        test_telemetry = {
            "lot_code": "KAFKA-TEST-001",
            "cycle_time": 45.5,
            "cutting_depth": 2.5,
            "vibration": 150.0,
            "tool_alarms": "None",
            "local_timestamp": "2024-12-20T11:21:41+01:00",
            "utc_timestamp": "2024-12-20T10:21:41Z",
            "site": "Italy",
            "machine_id": "cnc_Italy_1"
        }
        
        result = await kafka_sender.send_telemetry_data(test_telemetry, "fresa_cnc")
        assert result == True, "Failed to send telemetry data"
        
        # Test production completion sending
        test_completion = {
            "lot_code": "KAFKA-TEST-001",
            "customer": "Test Customer",
            "quantity": 100,
            "site": "Italy",
            "local_timestamp": "2024-12-20T16:45:00+01:00",
            "completion_timestamp": "2024-12-20T15:45:00Z",
            "total_duration_minutes": 5,  # Accelerated time
            "cnc_duration": 1,
            "lathe_duration": 1,
            "assembly_duration": 2,
            "test_duration": 1,
            "result": "COMPLETED"
        }
        
        result = await kafka_sender.send_production_completion_data(test_completion)
        assert result == True, "Failed to send production completion data"
        
        await kafka_sender.stop()
        self.test_results["kafka_integration"] = True
        print("✅ Kafka integration working correctly")
    
    async def test_high_frequency_telemetry(self):
        """Test high-frequency telemetry concept (without full simulator)"""
        print("\n⚡ Testing high-frequency telemetry concept...")
        
        # Test that the telemetry interval is set correctly
        from Simulator.state_machine import ProductionCoordinator
        
        coordinator = ProductionCoordinator(None)
        assert hasattr(coordinator, 'telemetry_interval'), "Telemetry interval not configured"
        assert coordinator.telemetry_interval == 1.0, f"Telemetry interval should be 1.0, got {coordinator.telemetry_interval}"
        assert hasattr(coordinator, 'telemetry_enabled'), "Telemetry enabled flag not configured"
        
        self.test_results["high_frequency_telemetry"] = True
        print("✅ High-frequency telemetry configured correctly")
    
    async def test_end_to_end_cycle(self):
        """Test a complete accelerated cycle"""
        print("\n🔄 Testing end-to-end accelerated cycle...")
        
        # This test would require starting the full simulator
        # For now, we'll test the components individually
        
        # Test that all components can be initialized
        try:
            config = load_config()
            simulator = CoffeeMekSimulator(config)
            
            # Test that simulator can be created without errors
            assert simulator is not None, "Failed to create simulator"
            assert simulator.kafka_sender is not None, "Kafka sender not initialized"
            assert simulator.production_coordinator is not None, "Production coordinator not initialized"
            
            self.test_results["end_to_end_cycle"] = True
            print("✅ End-to-end cycle components initialized correctly")
            
        except Exception as e:
            print(f"❌ End-to-end cycle test failed: {e}")
            self.test_results["end_to_end_cycle"] = False
    
    async def run_all_tests(self):
        """Run all accelerated simulator tests"""
        print("🧪 Starting Accelerated Simulator Tests...\n")
        print("Testing Configuration:")
        print("  • Accelerated processing: 1-2 minutes per stage")
        print("  • High-frequency telemetry: 1-second intervals")
        print("  • Real-time monitoring enabled")
        print("  • Specification compliance maintained")
        
        try:
            await self.test_accelerated_processing_times()
            await self.test_monitoring_system()
            await self.test_specification_compliance()
            await self.test_kafka_integration()
            await self.test_high_frequency_telemetry()
            await self.test_end_to_end_cycle()
            
            # Summary
            print("\n" + "="*50)
            print("🎉 TEST RESULTS SUMMARY")
            print("="*50)
            
            all_passed = True
            for test_name, result in self.test_results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status} {test_name.replace('_', ' ').title()}")
                if not result:
                    all_passed = False
            
            print("="*50)
            if all_passed:
                print("🎉 ALL TESTS PASSED! Accelerated simulator is ready for testing.")
                print("\nNext steps:")
                print("  1. Install dependencies: pip install rich aiohttp-cors")
                print("  2. Start console interface: python simulator_control.py console")
                print("  3. Start web interface: python simulator_control.py web")
                return True
            else:
                print("❌ Some tests failed. Please check the errors above.")
                return False
                
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main test function"""
    tester = AcceleratedSimulatorTest()
    success = await tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
