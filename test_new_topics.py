#!/usr/bin/env python3
"""
Test script to verify the new measurement and end-of-cycle topics functionality
"""

import asyncio
import json
import sys
from datetime import datetime
from dataclasses import asdict

# Add the Simulator module to the path
sys.path.append('.')

from Simulator.models import (
    CNCMeasurementData, DrillMeasurementData, 
    AssemblyMeasurementData, TestMeasurementData,
    EndOfCycleData, Location
)
from Simulator.Machine import get_machine_simulator
from Simulator.kafka_integration import KafkaDataSender

class NewTopicsTest:
    """Test the new measurement and end-of-cycle functionality"""
    
    def __init__(self):
        self.config = {
            "kafka": {
                "bootstrap_servers": "165.227.168.240:9093"
            }
        }
        self.kafka_sender = None
    
    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up test environment...")
        self.kafka_sender = KafkaDataSender(self.config)
        await self.kafka_sender.start()
        print("✅ Kafka connection established")
    
    async def cleanup(self):
        """Cleanup test environment"""
        if self.kafka_sender:
            await self.kafka_sender.stop()
        print("🧹 Test environment cleaned up")
    
    def test_measurement_data_models(self):
        """Test measurement data model creation"""
        print("\n📊 Testing measurement data models...")
        
        # Test CNC measurement data
        cnc_data = CNCMeasurementData(
            codice_lotto="TEST-001",
            factory_key="IT_1",
            timestamp_locale="2025-06-25T15:30:00+01:00",
            timestamp_utc="2025-06-25T14:30:00Z",
            luogo="Italia",
            tempo_ciclo=45.5,
            profondita_taglio=2.5,
            vibrazione=150.0,
            precisione_dimensionale=0.01,
            usura_utensile=25.5
        )
        
        cnc_dict = asdict(cnc_data)
        assert cnc_dict["factory_key"] == "IT_1"
        assert cnc_dict["tempo_ciclo"] == 45.5
        print("✅ CNC measurement data model works")
        
        # Test Drill measurement data
        drill_data = DrillMeasurementData(
            codice_lotto="TEST-001",
            factory_key="BR_2",
            timestamp_locale="2025-06-25T11:30:00-03:00",
            timestamp_utc="2025-06-25T14:30:00Z",
            luogo="Brasile",
            velocita_rotazione=1500.0,
            temperatura_mandrino=45.0,
            numero_pezzi_completati=50,
            precisione_foro=0.005,
            coppia_torsione=120.0
        )
        
        drill_dict = asdict(drill_data)
        assert drill_dict["factory_key"] == "BR_2"
        assert drill_dict["velocita_rotazione"] == 1500.0
        print("✅ Drill measurement data model works")
        
        print("✅ All measurement data models working correctly")
    
    def test_end_of_cycle_data_model(self):
        """Test end-of-cycle data model"""
        print("\n🏁 Testing end-of-cycle data model...")
        
        cycle_data = EndOfCycleData(
            location="Italia",
            codice_lotto="TEST-001",
            timestamp_locale="2025-06-25T15:30:00+01:00",
            timestamp_utc="2025-06-25T14:30:00Z",
            tempo_per_macchina={
                "fresa_cnc_Italia_1": 45.5,
                "tornio_Italia_1": 30.2,
                "assemblaggio_Italia_1": 60.8,
                "test_Italia_1": 15.3
            },
            numero_pezzi_completati=100,
            tempo_totale_ciclo=151.8,
            efficienza_complessiva=85.5
        )
        
        cycle_dict = asdict(cycle_data)
        assert cycle_dict["location"] == "Italia"
        assert len(cycle_dict["tempo_per_macchina"]) == 4
        print("✅ End-of-cycle data model works")
    
    def test_machine_simulators_measurement_data(self):
        """Test that machine simulators can generate measurement data"""
        print("\n🏭 Testing machine simulators measurement data generation...")
        
        # Test CNC simulator
        cnc_simulator = get_machine_simulator("fresa_cnc_Italia_1", "fresa_cnc", "Italia")
        if cnc_simulator:
            cnc_simulator.current_lot = "TEST-001"
            measurement_data = cnc_simulator.generate_measurement_data()
            
            assert "factory_key" in measurement_data
            assert "tempo_ciclo" in measurement_data
            assert measurement_data["codice_lotto"] == "TEST-001"
            print("✅ CNC simulator measurement data generation works")
        
        # Test Tornio simulator
        tornio_simulator = get_machine_simulator("tornio_Brasile_1", "tornio", "Brasile")
        if tornio_simulator:
            tornio_simulator.current_lot = "TEST-002"
            measurement_data = tornio_simulator.generate_measurement_data()
            
            assert "factory_key" in measurement_data
            assert "velocita_rotazione" in measurement_data
            assert measurement_data["codice_lotto"] == "TEST-002"
            print("✅ Tornio simulator measurement data generation works")
        
        print("✅ All machine simulators generating measurement data correctly")
    
    async def test_kafka_topic_sending(self):
        """Test sending data to new Kafka topics"""
        print("\n📡 Testing Kafka topic sending...")
        
        # Test measurement data sending
        measurement_data = {
            "codice_lotto": "TEST-001",
            "factory_key": "IT_1",
            "timestamp_locale": "2025-06-25T15:30:00+01:00",
            "timestamp_utc": "2025-06-25T14:30:00Z",
            "luogo": "Italia",
            "tempo_ciclo": 45.5,
            "profondita_taglio": 2.5,
            "vibrazione": 150.0,
            "precisione_dimensionale": 0.01,
            "usura_utensile": 25.5
        }
        
        result = await self.kafka_sender.send_measurement_data(measurement_data, "fresa_cnc")
        assert result == True
        print("✅ Measurement data sent to coffeemek.measurement.cnc")
        
        # Test end-of-cycle data sending
        cycle_data = {
            "location": "Italia",
            "codice_lotto": "TEST-001",
            "timestamp_locale": "2025-06-25T15:30:00+01:00",
            "timestamp_utc": "2025-06-25T14:30:00Z",
            "tempo_per_macchina": {
                "fresa_cnc_Italia_1": 45.5,
                "tornio_Italia_1": 30.2
            },
            "numero_pezzi_completati": 100,
            "tempo_totale_ciclo": 151.8,
            "efficienza_complessiva": 85.5
        }
        
        result = await self.kafka_sender.send_end_of_cycle_data(cycle_data, "Italia")
        assert result == True
        print("✅ End-of-cycle data sent to coffeemek.cycle.italy")
        
        print("✅ All Kafka topic sending working correctly")
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting new topics functionality tests...\n")
        
        try:
            # Setup
            await self.setup()
            
            # Run tests
            self.test_measurement_data_models()
            self.test_end_of_cycle_data_model()
            self.test_machine_simulators_measurement_data()
            await self.test_kafka_topic_sending()
            
            print("\n🎉 All tests passed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await self.cleanup()

async def main():
    """Main test function"""
    tester = NewTopicsTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ New topics functionality is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
