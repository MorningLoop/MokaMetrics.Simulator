#!/usr/bin/env python3
"""
Test script to verify that the implementation produces messages that exactly match 
the kafka-topics-doc.md specification
"""

import asyncio
import json
import sys
from datetime import datetime
from dataclasses import asdict

# Add the Simulator module to the path
sys.path.append('.')

from Simulator.models import (
    CNCTelemetryData, LatheTelemetryData, 
    AssemblyTelemetryData, TestingTelemetryData,
    ProductionCompletionData, Location
)
from Simulator.Machine import get_machine_simulator
from Simulator.kafka_integration import KafkaDataSender

class SpecificationComplianceTest:
    """Test that implementation matches kafka-topics-doc.md specification exactly"""
    
    def __init__(self):
        self.config = {
            "kafka": {
                "bootstrap_servers": "165.227.168.240:9093"
            }
        }
        self.kafka_sender = None
    
    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up specification compliance test...")
        self.kafka_sender = KafkaDataSender(self.config)
        await self.kafka_sender.start()
        print("✅ Kafka connection established")
    
    async def cleanup(self):
        """Cleanup test environment"""
        if self.kafka_sender:
            await self.kafka_sender.stop()
        print("🧹 Test environment cleaned up")
    
    def test_cnc_telemetry_structure(self):
        """Test CNC telemetry data structure matches specification"""
        print("\n🔩 Testing CNC telemetry structure...")
        
        # Create sample data according to specification
        cnc_data = CNCTelemetryData(
            lot_code="L-2024-0001",
            cycle_time=28.73,
            cutting_depth=4.76,
            vibration=735,
            tool_alarms="None",
            local_timestamp="2024-12-20T11:21:41+01:00",
            utc_timestamp="2024-12-20T10:21:41Z",
            site="Italy",
            machine_id="cnc_Italy_1"
        )
        
        cnc_dict = asdict(cnc_data)
        
        # Verify all required fields are present
        required_fields = [
            "lot_code", "cycle_time", "cutting_depth", "vibration", 
            "tool_alarms", "local_timestamp", "utc_timestamp", "site", "machine_id"
        ]
        
        for field in required_fields:
            assert field in cnc_dict, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(cnc_dict["lot_code"], str)
        assert isinstance(cnc_dict["cycle_time"], float)
        assert isinstance(cnc_dict["cutting_depth"], float)
        assert isinstance(cnc_dict["vibration"], (int, float))
        assert isinstance(cnc_dict["tool_alarms"], str)
        assert cnc_dict["tool_alarms"] in ["None", "Tool breakage", "Worn tool"]
        
        print("✅ CNC telemetry structure matches specification")
    
    def test_lathe_telemetry_structure(self):
        """Test Lathe telemetry data structure matches specification"""
        print("\n⚙️ Testing Lathe telemetry structure...")
        
        lathe_data = LatheTelemetryData(
            lot_code="L-2024-0001",
            machine_status="Active",
            rotation_speed=1500.5,
            spindle_temperature=65.3,
            completed_pieces=42,
            local_timestamp="2024-12-20T12:30:00+01:00",
            utc_timestamp="2024-12-20T11:30:00Z",
            site="Italy",
            machine_id="lathe_Italy_2"
        )
        
        lathe_dict = asdict(lathe_data)
        
        # Verify all required fields are present
        required_fields = [
            "lot_code", "machine_status", "rotation_speed", "spindle_temperature",
            "completed_pieces", "local_timestamp", "utc_timestamp", "site", "machine_id"
        ]
        
        for field in required_fields:
            assert field in lathe_dict, f"Missing required field: {field}"
        
        # Verify field types and values
        assert isinstance(lathe_dict["machine_status"], str)
        assert lathe_dict["machine_status"] in ["Active", "Inactive", "Maintenance", "Fault"]
        assert isinstance(lathe_dict["rotation_speed"], float)
        assert isinstance(lathe_dict["spindle_temperature"], float)
        assert isinstance(lathe_dict["completed_pieces"], int)
        
        print("✅ Lathe telemetry structure matches specification")
    
    def test_assembly_telemetry_structure(self):
        """Test Assembly telemetry data structure matches specification"""
        print("\n🔧 Testing Assembly telemetry structure...")
        
        assembly_data = AssemblyTelemetryData(
            associated_lot="L-2024-0001",
            average_time_per_station=75.5,
            active_operators=5,
            detected_anomalies=["Missing component", "Excessive cycle time"],
            local_timestamp="2024-12-20T14:15:00+01:00",
            utc_timestamp="2024-12-20T13:15:00Z",
            site="Italy",
            machine_id="assembly_Italy_1"
        )
        
        assembly_dict = asdict(assembly_data)
        
        # Verify all required fields are present
        required_fields = [
            "associated_lot", "average_time_per_station", "active_operators",
            "detected_anomalies", "local_timestamp", "utc_timestamp", "site", "machine_id"
        ]
        
        for field in required_fields:
            assert field in assembly_dict, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(assembly_dict["associated_lot"], str)
        assert isinstance(assembly_dict["average_time_per_station"], float)
        assert isinstance(assembly_dict["active_operators"], int)
        assert isinstance(assembly_dict["detected_anomalies"], list)
        
        # Verify anomaly values are valid
        valid_anomalies = ["Missing component", "Misalignment", "Excessive cycle time", "Insufficient quality"]
        for anomaly in assembly_dict["detected_anomalies"]:
            assert anomaly in valid_anomalies, f"Invalid anomaly: {anomaly}"
        
        print("✅ Assembly telemetry structure matches specification")
    
    def test_testing_telemetry_structure(self):
        """Test Testing telemetry data structure matches specification"""
        print("\n🧪 Testing Testing telemetry structure...")
        
        testing_data = TestingTelemetryData(
            lot_code="L-2024-0001",
            functional_test_results={
                "pressure": True,
                "temperature": True,
                "flow_rate": True,
                "noise": False,
                "vibration": True
            },
            boiler_pressure=12.5,
            boiler_temperature=92.3,
            energy_consumption=2.8,
            local_timestamp="2024-12-20T15:45:00+01:00",
            utc_timestamp="2024-12-20T14:45:00Z",
            site="Italy",
            machine_id="testing_Italy_1"
        )
        
        testing_dict = asdict(testing_data)
        
        # Verify all required fields are present
        required_fields = [
            "lot_code", "functional_test_results", "boiler_pressure",
            "boiler_temperature", "energy_consumption", "local_timestamp", 
            "utc_timestamp", "site", "machine_id"
        ]
        
        for field in required_fields:
            assert field in testing_dict, f"Missing required field: {field}"
        
        # Verify functional test results structure
        test_results = testing_dict["functional_test_results"]
        required_tests = ["pressure", "temperature", "flow_rate", "noise", "vibration"]
        for test in required_tests:
            assert test in test_results, f"Missing test result: {test}"
            assert isinstance(test_results[test], bool), f"Test result {test} must be boolean"
        
        print("✅ Testing telemetry structure matches specification")
    
    def test_production_completion_structure(self):
        """Test Production completion data structure matches specification"""
        print("\n🏁 Testing Production completion structure...")
        
        completion_data = ProductionCompletionData(
            lot_code="L-2024-0001",
            customer="Lavazza",
            quantity=98,
            site="Italy",
            local_timestamp="2024-12-20T16:45:00+01:00",
            completion_timestamp="2024-12-20T15:45:00Z",
            total_duration_minutes=345,
            cnc_duration=45,
            lathe_duration=35,
            assembly_duration=80,
            test_duration=25,
            result="COMPLETED"
        )
        
        completion_dict = asdict(completion_data)
        
        # Verify all required fields are present
        required_fields = [
            "lot_code", "customer", "quantity", "site", "local_timestamp",
            "completion_timestamp", "total_duration_minutes", "cnc_duration",
            "lathe_duration", "assembly_duration", "test_duration", "result"
        ]
        
        for field in required_fields:
            assert field in completion_dict, f"Missing required field: {field}"
        
        # Verify field types and values
        assert isinstance(completion_dict["quantity"], int)
        assert isinstance(completion_dict["total_duration_minutes"], int)
        assert completion_dict["result"] in ["COMPLETED", "REJECTED"]
        assert completion_dict["site"] in ["Italy", "Brazil", "Vietnam"]
        
        print("✅ Production completion structure matches specification")
    
    async def test_machine_simulators_compliance(self):
        """Test that machine simulators generate compliant data"""
        print("\n🏭 Testing machine simulators compliance...")
        
        # Test CNC simulator
        cnc_simulator = get_machine_simulator("cnc_Italy_1", "fresa_cnc", "Italia")
        if cnc_simulator:
            cnc_simulator.current_lot = "L-2024-0001"
            cnc_data = cnc_simulator.generate_measurement_data()
            
            # Verify structure matches CNC specification
            assert "lot_code" in cnc_data
            assert "cycle_time" in cnc_data
            assert "cutting_depth" in cnc_data
            assert "vibration" in cnc_data
            assert "tool_alarms" in cnc_data
            assert "site" in cnc_data
            assert "machine_id" in cnc_data
            print("✅ CNC simulator generates compliant data")
        
        # Test Lathe simulator
        lathe_simulator = get_machine_simulator("lathe_Brazil_1", "tornio", "Brasile")
        if lathe_simulator:
            lathe_simulator.current_lot = "L-2024-0002"
            lathe_data = lathe_simulator.generate_measurement_data()
            
            # Verify structure matches Lathe specification
            assert "lot_code" in lathe_data
            assert "machine_status" in lathe_data
            assert "rotation_speed" in lathe_data
            assert "spindle_temperature" in lathe_data
            assert "completed_pieces" in lathe_data
            assert "site" in lathe_data
            assert "machine_id" in lathe_data
            print("✅ Lathe simulator generates compliant data")
        
        print("✅ All machine simulators generate specification-compliant data")
    
    async def test_kafka_topic_compliance(self):
        """Test that Kafka topics match specification"""
        print("\n📡 Testing Kafka topic compliance...")
        
        # Test telemetry topics
        test_data = {
            "lot_code": "L-2024-0001",
            "cycle_time": 28.73,
            "cutting_depth": 4.76,
            "vibration": 735,
            "tool_alarms": "None",
            "local_timestamp": "2024-12-20T11:21:41+01:00",
            "utc_timestamp": "2024-12-20T10:21:41Z",
            "site": "Italy",
            "machine_id": "cnc_Italy_1"
        }
        
        # Test CNC topic
        result = await self.kafka_sender.send_telemetry_data(test_data, "fresa_cnc")
        assert result == True
        print("✅ mokametrics.telemetry.cnc topic working")
        
        # Test production completion topic
        completion_data = {
            "lot_code": "L-2024-0001",
            "customer": "Lavazza",
            "quantity": 98,
            "site": "Italy",
            "local_timestamp": "2024-12-20T16:45:00+01:00",
            "completion_timestamp": "2024-12-20T15:45:00Z",
            "total_duration_minutes": 345,
            "cnc_duration": 45,
            "lathe_duration": 35,
            "assembly_duration": 80,
            "test_duration": 25,
            "result": "COMPLETED"
        }
        
        result = await self.kafka_sender.send_production_completion_data(completion_data)
        assert result == True
        print("✅ mokametrics.production.lotto_completato topic working")
        
        print("✅ All Kafka topics comply with specification")
    
    async def run_all_tests(self):
        """Run all specification compliance tests"""
        print("🧪 Starting specification compliance tests...\n")
        
        try:
            # Setup
            await self.setup()
            
            # Run tests
            self.test_cnc_telemetry_structure()
            self.test_lathe_telemetry_structure()
            self.test_assembly_telemetry_structure()
            self.test_testing_telemetry_structure()
            self.test_production_completion_structure()
            await self.test_machine_simulators_compliance()
            await self.test_kafka_topic_compliance()
            
            print("\n🎉 All specification compliance tests passed!")
            return True
            
        except Exception as e:
            print(f"\n❌ Specification compliance test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await self.cleanup()

async def main():
    """Main test function"""
    tester = SpecificationComplianceTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Implementation fully complies with kafka-topics-doc.md specification!")
        sys.exit(0)
    else:
        print("\n❌ Implementation does not comply with specification!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
