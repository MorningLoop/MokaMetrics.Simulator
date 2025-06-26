"""
Test line machine simulator
"""

from typing import Dict, Any
import random
from dataclasses import asdict

from .base import MachineSimulator
from ..models import TestLineData, TestingTelemetryData, Location

class TestSimulator(MachineSimulator):
    """Simulator for test line"""
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate telemetry data for Test Line"""
        local_time, utc_time = self.get_timestamps()
        is_blocked, block_reason = self.check_machine_block()
        
        # Generate test results
        test_types = ["Pressure", "Temperature", "Flow", "Noise", "Vibration"]
        test_results = {test: random.random() > 0.05 for test in test_types}  # 95% pass rate
        
        # Update machine status and pieces produced
        current_status = self.get_machine_status()
        if current_status == "working":
            # Simulate pieces tested during this cycle
            pieces_this_cycle = random.randint(1, 8)  # Test line processes multiple pieces
            self.increment_pieces_produced(pieces_this_cycle)

        data = TestLineData(
            lot_code=self.generate_lot_code(),
            functional_test_results=test_results,
            boiler_pressure=round(random.uniform(8, 15), 2),
            boiler_temperature=round(random.uniform(85, 95), 2),
            energy_consumption=round(random.uniform(1.5, 3.5), 2),
            location=self.location.value[0],
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            machine_blocked=is_blocked,
            block_reason=block_reason or "",
            last_maintenance=self.last_maintenance.isoformat(),
            machine="Test Line",
            total_pieces_produced=self.total_pieces_produced,
            machine_status=current_status
        )
        
        return asdict(data)

    def generate_measurement_data(self) -> Dict[str, Any]:
        """Generate telemetry data for testing machine according to mokametrics.telemetry.testing specification"""
        local_time, utc_time = self.get_timestamps()

        # Generate functional test results according to specification
        functional_test_results = {
            "pressure": random.random() > 0.05,  # 95% pass rate
            "temperature": random.random() > 0.05,
            "flow_rate": random.random() > 0.05,
            "noise": random.random() > 0.05,
            "vibration": random.random() > 0.05
        }

        # Generate telemetry data according to specification
        boiler_pressure = round(random.uniform(8, 15), 1)  # Boiler pressure in bar
        boiler_temperature = round(random.uniform(85, 95), 1)  # Boiler temperature in °C
        energy_consumption = round(random.uniform(1.5, 4.0), 1)  # Energy consumption in kWh

        # Map location to site name
        site_mapping = {
            "Italy": "Italy",
            "Brazil": "Brazil",
            "Vietnam": "Vietnam"
        }
        site = site_mapping.get(self.location.value[0], "Italy")

        # Update machine status and pieces produced
        current_status = self.get_machine_status()
        if current_status == "working":
            # Simulate pieces tested during this cycle
            pieces_this_cycle = random.randint(1, 8)  # Test line processes multiple pieces
            self.increment_pieces_produced(pieces_this_cycle)

        # Determine error message based on test results
        error_message = "None"
        failed_tests = [test for test, result in functional_test_results.items() if not result]
        if failed_tests:
            error_message = f"{failed_tests[0].title()} anomaly"

        telemetry_data = TestingTelemetryData(
            lot_code=self.generate_lot_code(),
            functional_test_results=functional_test_results,
            boiler_pressure=boiler_pressure,
            boiler_temperature=boiler_temperature,
            energy_consumption=energy_consumption,
            completed_pieces_since_last_maintenance=self.total_pieces_produced,
            error=error_message,
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            site=site,
            machine_id=self.machine_id,
            status=self.get_kafka_status()
        )

        return asdict(telemetry_data)

    def get_processing_time(self) -> int:
        """Get processing time for Test Line (1-2 minutes for testing)"""
        return random.randint(60, 120)  # 1-2 minutes in seconds