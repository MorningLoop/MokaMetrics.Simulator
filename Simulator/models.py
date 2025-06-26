"""
Data models for CoffeeMek simulator
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class Location(Enum):
    """Production locations with timezones"""
    ITALY = ("Italy", "Europe/Rome")
    BRAZIL = ("Brazil", "America/Sao_Paulo")
    VIETNAM = ("Vietnam", "Asia/Ho_Chi_Minh")

class AlarmType(Enum):
    """Types of machine alarms"""
    NONE = "None"
    TOOL_BREAKAGE = "Tool breakage"
    WORN_TOOL = "Worn tool"
    HIGH_TEMPERATURE = "High temperature"
    MAINTENANCE_REQUIRED = "Maintenance required"

class MachineState(Enum):
    """Machine operational states"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    MAINTENANCE = "Maintenance"
    FAULT = "Fault"

class MachineStatuses(Enum):
    """Machine status enum for Kafka telemetry (matches mokametrics specification)"""
    OPERATIONAL = 1  # Machine is operational and running normally
    MAINTENANCE = 2  # Machine is under maintenance
    ALARM = 3        # Machine is under alarm or has a critical issue
    OFFLINE = 4      # Machine is shut down
    IDLE = 5         # Machine is idle and not in production

@dataclass
class MachineData:
    """Base class for machine telemetry data"""
    lot_code: str
    location: str
    local_timestamp: str
    utc_timestamp: str
    machine_blocked: bool
    block_reason: Optional[str]
    last_maintenance: str
    machine: str
    # New general metrics
    total_pieces_produced: int
    machine_status: str  # "working", "idle", "error"

@dataclass
class CNCMillingData(MachineData):
    """Data model for CNC milling machine"""
    cycle_time: float
    cutting_depth: float
    vibration: float
    user_alarms: str

@dataclass
class LatheData(MachineData):
    """Data model for automatic lathe"""
    machine_state: str
    rotation_speed: float
    spindle_temperature: float
    completed_pieces_count: int

@dataclass
class AssemblyLineData(MachineData):
    """Data model for assembly line"""
    average_station_time: float
    operators_count: int
    detected_anomalies: List[str]

@dataclass
class TestLineData(MachineData):
    """Data model for test line"""
    functional_test_results: Dict[str, bool]
    boiler_pressure: float
    boiler_temperature: float
    energy_consumption: float

@dataclass
class CNCTelemetryData:
    """Telemetry data for CNC machines - matches mokametrics.telemetry.cnc specification"""
    lot_code: str
    cycle_time: float  # Processing time in minutes
    cutting_depth: float  # Cutting depth in mm
    vibration: float  # Vibration level (0-1000)
    completed_pieces_from_last_maintenance: int  # Counter of completed pieces since last maintenance
    error: str  # "None", "Tool breakage", "Worn tool"
    local_timestamp: str  # ISO 8601 with timezone
    utc_timestamp: str  # ISO 8601 UTC
    site: str  # "Italy", "Brazil", "Vietnam"
    machine_id: str  # Unique machine identifier
    status: int  # MachineStatuses enum (1=Operational, 2=Maintenance, 3=Alarm, 4=Offline, 5=Idle)

@dataclass
class LatheTelemetryData:
    """Telemetry data for lathe machines - matches mokametrics.telemetry.lathe specification"""
    lot_code: str
    cycle_time: float  # Processing time in minutes
    rotation_speed: float  # Rotation speed in RPM
    spindle_temperature: float  # Spindle temperature in °C
    completed_pieces_from_last_maintenance: int  # Counter of completed pieces since last maintenance
    error: str  # "None", "Tool breakage", "Worn tool"
    local_timestamp: str  # ISO 8601 with timezone
    utc_timestamp: str  # ISO 8601 UTC
    site: str  # "Italy", "Brazil", "Vietnam"
    machine_id: str  # Unique machine identifier
    status: int  # MachineStatuses enum (1=Operational, 2=Maintenance, 3=Alarm, 4=Offline, 5=Idle)

@dataclass
class AssemblyTelemetryData:
    """Telemetry data for assembly machines - matches mokametrics.telemetry.assembly specification"""
    lot_code: str
    cycle_time: float  # Processing time in minutes
    active_operators: int  # Number of active operators on the line
    completed_pieces_since_last_maintenance: int  # Counter of completed pieces since last maintenance
    error: str  # "None", "Missing component", "Misalignment", "Excessive cycle time", "Insufficient quality"
    local_timestamp: str  # ISO 8601 with timezone
    utc_timestamp: str  # ISO 8601 UTC
    site: str  # "Italy", "Brazil", "Vietnam"
    machine_id: str  # Unique machine identifier
    status: int  # MachineStatuses enum (1=Operational, 2=Maintenance, 3=Alarm, 4=Offline, 5=Idle)

@dataclass
class TestingTelemetryData:
    """Telemetry data for testing machines - matches mokametrics.telemetry.testing specification"""
    lot_code: str
    functional_test_results: Dict[str, bool]  # Test results (true = passed, false = failed)
    boiler_pressure: float  # Boiler pressure in bar
    boiler_temperature: float  # Boiler temperature in °C
    energy_consumption: float  # Energy consumption in kWh
    completed_pieces_since_last_maintenance: int  # Counter of completed pieces since last maintenance
    error: str  # "None", "Pressure anomaly", "Temperature anomaly", "Flow rate anomaly", "Noise anomaly", "Vibration anomaly"
    local_timestamp: str  # ISO 8601 with timezone
    utc_timestamp: str  # ISO 8601 UTC
    site: str  # "Italy", "Brazil", "Vietnam"
    machine_id: str  # Unique machine identifier
    status: int  # MachineStatuses enum (1=Operational, 2=Maintenance, 3=Alarm, 4=Offline, 5=Idle)

@dataclass
class ProductionCompletionData:
    """Production completion data - matches mokametrics.production.lotto_completato specification"""
    lot_code: str
    customer: str
    quantity: int
    site: str  # "Italy", "Brazil", "Vietnam"
    local_timestamp: str  # Local completion timestamp with timezone
    completion_timestamp: str  # UTC completion timestamp
    total_duration_minutes: int  # Total time from first to last processing
    cnc_duration: int  # Processing minutes in CNC milling
    lathe_duration: int  # Processing minutes in lathe
    assembly_duration: int  # Processing minutes in assembly
    test_duration: int  # Processing minutes in test
    result: str  # "COMPLETED" or "REJECTED"