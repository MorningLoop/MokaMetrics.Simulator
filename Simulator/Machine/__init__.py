"""
Machine simulators factory
"""

from typing import Optional
from ..models import Location
from .base import MachineSimulator
from .fresa_cnc import CNCMillingSimulator
from .tornio import LatheSimulator
from .assemblaggio import AssemblySimulator
from .test import TestSimulator

# Cache for machine simulators
_machine_cache = {}

def get_machine_simulator(machine_id: str, machine_type: str, location_str: str) -> Optional[MachineSimulator]:
    """Get or create a machine simulator"""
    
    # Check cache first
    if machine_id in _machine_cache:
        return _machine_cache[machine_id]
    
    # Convert location string to Location enum
    location_map = {
        "Italy": Location.ITALY,
        "Brazil": Location.BRAZIL,
        "Vietnam": Location.VIETNAM
    }
    location = location_map.get(location_str)
    if not location:
        return None
    
    # Create appropriate simulator
    simulator = None
    if machine_type == "cnc" or machine_type == "fresa_cnc":
        simulator = CNCMillingSimulator(machine_id, location)
    elif machine_type == "lathe" or machine_type == "tornio":
        simulator = LatheSimulator(machine_id, location)
    elif machine_type == "assembly" or machine_type == "assemblaggio":
        simulator = AssemblySimulator(machine_id, location)
    elif machine_type == "test":
        simulator = TestSimulator(machine_id, location)
    
    # Cache it
    if simulator:
        _machine_cache[machine_id] = simulator
    
    return simulator

__all__ = [
    'MachineSimulator',
    'CNCMillingSimulator', 
    'LatheSimulator',
    'AssemblySimulator',
    'TestSimulator',
    'get_machine_simulator'
]