"""
CNC Milling machine simulator
"""

from typing import Dict, Any
import random
from dataclasses import asdict

from .base import MachineSimulator
from ..models import CNCMillingData, CNCTelemetryData, Location, AlarmType

class CNCMillingSimulator(MachineSimulator):
    """Simulator for CNC milling machine"""
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate telemetry data for CNC Milling Machine"""
        local_time, utc_time = self.get_timestamps()
        is_blocked, block_reason = self.check_machine_block()
        
        # Generate realistic data ranges
        cycle_time = round(random.uniform(10, 60), 2)
        cutting_depth = round(random.uniform(0.1, 5.0), 2)
        vibration = round(random.uniform(0.01, 800), 2)
        
        # Determine alarms based on conditions
        alarms = AlarmType.NONE.value
        if vibration > 600:
            alarms = random.choice([
                AlarmType.TOOL_BREAKAGE.value,
                AlarmType.WORN_TOOL.value
            ])
        
        # Update machine status and pieces produced
        current_status = self.get_machine_status()
        if current_status == "working":
            # Simulate pieces produced during this cycle
            pieces_this_cycle = random.randint(1, 5)
            self.increment_pieces_produced(pieces_this_cycle)

        data = CNCMillingData(
            lot_code=self.generate_lot_code(),
            cycle_time=cycle_time,
            cutting_depth=cutting_depth,
            vibration=vibration,
            user_alarms=alarms,
            location=self.location.value[0],
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            machine_blocked=is_blocked,
            block_reason=block_reason or "",
            last_maintenance=self.last_maintenance.isoformat(),
            machine="CNC Milling Machine",
            total_pieces_produced=self.total_pieces_produced,
            machine_status=current_status
        )
        
        return asdict(data)

    def generate_measurement_data(self) -> Dict[str, Any]:
        """Generate telemetry data for CNC machine according to mokametrics.telemetry.cnc specification"""
        local_time, utc_time = self.get_timestamps()

        # Generate telemetry data according to specification
        cycle_time = round(random.uniform(10, 60), 2)  # Processing time in minutes
        cutting_depth = round(random.uniform(0.1, 5.0), 2)  # Cutting depth in mm
        vibration = round(random.uniform(0, 1000), 2)  # Vibration level (0-1000)

        # Determine tool alarms based on conditions
        tool_alarms = "None"
        if vibration > 800:
            tool_alarms = random.choice(["Tool breakage", "Worn tool"])

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
            pieces_this_cycle = random.randint(1, 5)
            self.increment_pieces_produced(pieces_this_cycle)

        telemetry_data = CNCTelemetryData(
            lot_code=self.generate_lot_code(),
            cycle_time=cycle_time,
            cutting_depth=cutting_depth,
            vibration=vibration,
            completed_pieces_from_last_maintenance=self.total_pieces_produced,
            error=tool_alarms,
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            site=site,
            machine_id=self.machine_id,
            status=self.get_kafka_status()
        )

        return asdict(telemetry_data)

    def get_processing_time(self) -> int:
        """Get processing time for CNC Milling Machine (1-2 minutes for testing)"""
        return random.randint(60, 120)  # 1-2 minutes in seconds