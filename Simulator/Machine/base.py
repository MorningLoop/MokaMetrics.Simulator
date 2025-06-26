"""
Base class for machine simulators
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
import random
import pytz
from ..models import Location, MachineStatuses

class MachineSimulator(ABC):
    """Abstract base class for all machine simulators"""

    def __init__(self, machine_id: str, location: Location):
        self.machine_id = machine_id
        self.location = location
        self.last_maintenance = datetime.now() - timedelta(days=random.randint(1, 90))
        self.is_blocked = False
        self.block_reason = None
        self.current_lot = None
        self.processing_start_time = None
        self.expected_completion_time = None
        # New metrics
        self.total_pieces_produced = random.randint(0, 1000)  # Initialize with some history
        self.current_status = "idle"  # "working", "idle", "error"
        self._manual_status_override = False  # Flag to track manual status updates
        
    @abstractmethod
    def generate_data(self) -> Dict[str, Any]:
        """Generate telemetry data for the machine"""
        pass

    @abstractmethod
    def generate_measurement_data(self) -> Dict[str, Any]:
        """Generate measurement data with factory key"""
        pass

    @abstractmethod
    def get_processing_time(self) -> int:
        """Get expected processing time in seconds for current lot"""
        pass
    
    def get_timestamps(self) -> tuple:
        """Get local and UTC timestamps"""
        utc_now = datetime.now(timezone.utc)
        local_tz = pytz.timezone(self.location.value[1])
        local_now = utc_now.astimezone(local_tz)
        
        return (
            local_now.isoformat(),
            utc_now.isoformat()
        )
    
    def generate_lot_code(self) -> str:
        """Generate a realistic lot code - or use current lot if assigned"""
        if self.current_lot:
            return self.current_lot
        return f"L-{random.randint(1000, 9999)}"

    def generate_factory_key(self) -> str:
        """Generate factory key based on location and machine"""
        location_mapping = {
            "Italy": "IT",
            "Brazil": "BR",
            "Vietnam": "VN"
        }
        prefix = location_mapping.get(self.location.value[0], "XX")
        machine_suffix = self.machine_id.split("_")[-1]  # Get machine number
        return f"{prefix}_{machine_suffix}"
    
    def check_machine_block(self) -> tuple:
        """Randomly determine if machine is blocked"""
        if random.random() < 0.05:  # 5% chance of block
            reasons = [
                "Urgent maintenance",
                "Component failure",
                "Quality control",
                "Tool change"
            ]
            return True, random.choice(reasons)
        return False, None

    def get_machine_status(self) -> str:
        """Determine current machine status based on state"""
        # If status was manually set (e.g., by state machine), use that
        if hasattr(self, '_manual_status_override') and self._manual_status_override:
            return self.current_status

        # Otherwise, determine status automatically
        if self.is_blocked:
            return "error"
        elif self.current_lot and self.processing_start_time:
            return "working"
        else:
            return "idle"

    def increment_pieces_produced(self, count: int = 1):
        """Increment the total pieces produced counter"""
        self.total_pieces_produced += count

    def update_status(self, status: str):
        """Update machine status - should be 'working', 'idle', or 'error'"""
        if status in ["working", "idle", "error"]:
            self.current_status = status
            self._manual_status_override = True

    def get_kafka_status(self) -> int:
        """Convert internal status to Kafka status integer"""
        current_status = self.get_machine_status()

        # Map internal status to Kafka MachineStatuses enum
        status_mapping = {
            "working": MachineStatuses.OPERATIONAL.value,
            "idle": MachineStatuses.IDLE.value,
            "error": MachineStatuses.ALARM.value
        }

        return status_mapping.get(current_status, MachineStatuses.IDLE.value)

    def get_error_message(self) -> str:
        """Get error message based on machine state"""
        if self.is_blocked and self.block_reason:
            return self.block_reason
        return "None"
    