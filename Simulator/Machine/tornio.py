"""
Lathe machine simulator
"""

from typing import Dict, Any
import random
from dataclasses import asdict

from .base import MachineSimulator
from ..models import LatheData, LatheTelemetryData, Location, MachineState

class LatheSimulator(MachineSimulator):
    """Simulator for automatic lathe"""
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate telemetry data for Lathe"""
        local_time, utc_time = self.get_timestamps()
        is_blocked, block_reason = self.check_machine_block()
        
        # Generate realistic data
        rotation_speed = round(random.uniform(500, 3000), 2)
        spindle_temperature = round(random.uniform(20, 80), 2)
        completed_pieces_count = random.randint(0, 100)
        
        # Determine machine state
        if is_blocked:
            machine_state = MachineState.FAULT.value
        else:
            machine_state = random.choice([s.value for s in MachineState if s != MachineState.FAULT])
        
        # Update machine status and pieces produced
        current_status = self.get_machine_status()
        if current_status == "working":
            # Simulate pieces produced during this cycle
            pieces_this_cycle = random.randint(1, 3)
            self.increment_pieces_produced(pieces_this_cycle)

        data = LatheData(
            lot_code=self.generate_lot_code(),
            machine_state=machine_state,
            rotation_speed=rotation_speed,
            spindle_temperature=spindle_temperature,
            completed_pieces_count=completed_pieces_count,
            location=self.location.value[0],
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            machine_blocked=is_blocked,
            block_reason=block_reason or "",
            last_maintenance=self.last_maintenance.isoformat(),
            machine="Automatic Lathe",
            total_pieces_produced=self.total_pieces_produced,
            machine_status=current_status
        )
        
        return asdict(data)

    def generate_measurement_data(self) -> Dict[str, Any]:
        """Generate telemetry data for lathe machine according to mokametrics.telemetry.lathe specification"""
        local_time, utc_time = self.get_timestamps()
        is_blocked, block_reason = self.check_machine_block()

        # Generate telemetry data according to specification
        rotation_speed = round(random.uniform(500, 3000), 2)  # Rotation speed in RPM
        spindle_temperature = round(random.uniform(20, 80), 2)  # Spindle temperature in °C
        completed_pieces = random.randint(0, 100)  # Counter of completed pieces in the lot

        # Determine machine status
        if is_blocked:
            machine_status = "Fault"
        else:
            machine_status = random.choice(["Active", "Inactive", "Maintenance"])

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
            # Simulate pieces produced during this cycle
            pieces_this_cycle = random.randint(1, 3)
            self.increment_pieces_produced(pieces_this_cycle)

        # Calculate cycle time for Kafka compliance
        cycle_time = round(random.uniform(1, 5), 2)  # Processing time in minutes

        telemetry_data = LatheTelemetryData(
            lot_code=self.generate_lot_code(),
            cycle_time=cycle_time,
            rotation_speed=rotation_speed,
            spindle_temperature=spindle_temperature,
            completed_pieces_from_last_maintenance=self.total_pieces_produced,
            error=self.get_error_message(),
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            site=site,
            machine_id=self.machine_id,
            status=self.get_kafka_status()
        )

        return asdict(telemetry_data)

    def get_processing_time(self) -> int:
        """Get processing time for Lathe (1-2 minutes for testing)"""
        return random.randint(60, 120)  # 1-2 minutes in seconds