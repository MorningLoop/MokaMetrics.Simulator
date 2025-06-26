"""
Assembly line machine simulator
"""

from typing import Dict, Any
import random
from dataclasses import asdict

from .base import MachineSimulator
from ..models import AssemblyLineData, AssemblyTelemetryData, Location

class AssemblySimulator(MachineSimulator):
    """Simulator for assembly line"""
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate telemetry data for Assembly Line"""
        local_time, utc_time = self.get_timestamps()
        is_blocked, block_reason = self.check_machine_block()
        
        # Generate anomalies
        possible_anomalies = [
            "Missing component",
            "Misalignment",
            "Excessive cycle time",
            "Insufficient quality"
        ]
        anomalies = []
        if random.random() < 0.2:  # 20% chance of anomalies
            anomalies = random.sample(possible_anomalies, k=random.randint(1, 2))
        
        # Update machine status and pieces produced
        current_status = self.get_machine_status()
        if current_status == "working":
            # Simulate pieces produced during this cycle
            pieces_this_cycle = random.randint(5, 15)  # Assembly line produces more pieces
            self.increment_pieces_produced(pieces_this_cycle)

        data = AssemblyLineData(
            lot_code=self.generate_lot_code(),
            average_station_time=round(random.uniform(30, 120), 2),
            operators_count=random.randint(2, 8),
            detected_anomalies=anomalies,
            location=self.location.value[0],
            local_timestamp=local_time,
            utc_timestamp=utc_time,
            machine_blocked=is_blocked,
            block_reason=block_reason or "",
            last_maintenance=self.last_maintenance.isoformat(),
            machine="Assembly Line",
            total_pieces_produced=self.total_pieces_produced,
            machine_status=current_status
        )
        
        return asdict(data)

    def generate_measurement_data(self) -> Dict[str, Any]:
        """Generate telemetry data for assembly machine according to mokametrics.telemetry.assembly specification"""
        local_time, utc_time = self.get_timestamps()

        # Generate telemetry data according to specification
        average_time_per_station = round(random.uniform(30, 120), 2)  # Average time per station in seconds
        active_operators = random.randint(2, 8)  # Number of active operators on the line

        # Generate detected anomalies (can be empty)
        possible_anomalies = ["Missing component", "Misalignment", "Excessive cycle time", "Insufficient quality"]
        detected_anomalies = []
        if random.random() < 0.2:  # 20% chance of anomalies
            detected_anomalies = random.sample(possible_anomalies, k=random.randint(1, 2))

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
            pieces_this_cycle = random.randint(5, 15)  # Assembly line produces more pieces
            self.increment_pieces_produced(pieces_this_cycle)

        # Calculate cycle time for Kafka compliance
        cycle_time = round(average_time_per_station / 60, 2)  # Convert seconds to minutes

        # Convert detected anomalies to error string
        error_message = "None"
        if detected_anomalies:
            error_message = detected_anomalies[0]  # Use first anomaly as error

        telemetry_data = AssemblyTelemetryData(
            lot_code=self.generate_lot_code(),
            cycle_time=cycle_time,
            active_operators=active_operators,
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
        """Get processing time for Assembly Line (1-2 minutes for testing)"""
        return random.randint(60, 120)  # 1-2 minutes in seconds