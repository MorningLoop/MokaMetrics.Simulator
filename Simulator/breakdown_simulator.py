import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class BreakdownConfig:
    """Configuration for machine breakdown simulation"""
    enabled: bool = False
    breakdown_rate_per_hour: float = 0.1  # Average breakdowns per hour per machine
    min_interval_minutes: int = 30  # Minimum time between breakdowns
    max_interval_minutes: int = 480  # Maximum time between breakdowns (8 hours)
    
    # Breakdown types and their probabilities
    breakdown_types: Dict[str, float] = field(default_factory=lambda: {
        "mechanical": 0.4,  # Mechanical failures
        "electrical": 0.2,  # Electrical issues
        "software": 0.15,   # Software/control issues
        "tooling": 0.15,    # Tool wear/breakage
        "overheating": 0.1  # Thermal issues
    })
    
    # Breakdown reasons by type
    breakdown_reasons: Dict[str, List[str]] = field(default_factory=lambda: {
        "mechanical": [
            "Belt slippage detected",
            "Bearing wear excessive",
            "Spindle alignment error",
            "Drive mechanism failure",
            "Hydraulic pressure loss"
        ],
        "electrical": [
            "Motor overload protection triggered",
            "Control circuit fault",
            "Sensor communication error",
            "Power supply instability",
            "Emergency stop activated"
        ],
        "software": [
            "PLC communication timeout",
            "Program execution error",
            "Memory buffer overflow",
            "Axis calibration lost",
            "Control system restart required"
        ],
        "tooling": [
            "Cutting tool worn beyond limits",
            "Tool breakage detected",
            "Workpiece clamping failure",
            "Tool changer malfunction",
            "Measurement probe error"
        ],
        "overheating": [
            "Coolant system failure",
            "Thermal protection activated",
            "Spindle overtemperature",
            "Motor cooling insufficient",
            "Ambient temperature too high"
        ]
    })
    
    # Severity distribution
    severity_distribution: Dict[str, float] = field(default_factory=lambda: {
        "minor": 0.6,    # Quick fix, short downtime
        "major": 0.3,    # Significant repair needed
        "critical": 0.1  # Major intervention required
    })

class MachineBreakdownSimulator:
    """Simulates realistic machine breakdowns"""
    
    def __init__(self, config: BreakdownConfig = None):
        self.config = config or BreakdownConfig()
        self.running = False
        self.simulation_task = None
        self.machine_pools: Dict[str, any] = {}  # location -> MachinePool
        self.breakdown_callbacks: List[Callable] = []
        self.last_breakdown_times: Dict[str, datetime] = {}
        
    def register_machine_pool(self, location: str, machine_pool):
        """Register a machine pool for breakdown simulation"""
        self.machine_pools[location] = machine_pool
        logger.info(f"Registered machine pool for location: {location}")
    
    def add_breakdown_callback(self, callback: Callable):
        """Add callback function to be called when breakdown occurs"""
        self.breakdown_callbacks.append(callback)
    
    def start_simulation(self):
        """Start the breakdown simulation"""
        if self.config.enabled:
            if self.simulation_task is None or self.simulation_task.done():
                self.running = True
                self.simulation_task = asyncio.create_task(self._simulation_loop())
                logger.info("Machine breakdown simulation started")
            else:
                logger.info("Machine breakdown simulation already running")
    
    def stop_simulation(self):
        """Stop the breakdown simulation"""
        self.running = False
        if self.simulation_task and not self.simulation_task.done():
            self.simulation_task.cancel()
        logger.info("Machine breakdown simulation stopped")
    
    def update_config(self, config: BreakdownConfig):
        """Update breakdown configuration"""
        was_enabled = self.config.enabled
        self.config = config
        logger.info(f"Updated breakdown config - enabled: {config.enabled}, rate: {config.breakdown_rate_per_hour}/hour")
        logger.info(f"Config change: was_enabled={was_enabled}, now_enabled={config.enabled}")
        
        # Handle enabling/disabling simulation
        if config.enabled and not was_enabled:
            logger.info("Starting breakdown simulation due to config change")
            self.start_simulation()
        elif not config.enabled and was_enabled:
            logger.info("Stopping breakdown simulation due to config change")
            self.stop_simulation()
        else:
            logger.info(f"No simulation state change needed. enabled={config.enabled}, was_enabled={was_enabled}")
    
    async def _simulation_loop(self):
        """Main simulation loop"""
        logger.info("Breakdown simulation loop started")
        while self.running and self.config.enabled:
            try:
                # Check each machine pool
                for location, pool in self.machine_pools.items():
                    await self._check_machines_for_breakdown(location, pool)
                
                # Wait before next check (check every minute)
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in breakdown simulation loop: {e}")
                await asyncio.sleep(60)
        logger.info("Breakdown simulation loop ended")
    
    async def _check_machines_for_breakdown(self, location: str, machine_pool):
        """Check machines in a pool for potential breakdowns"""
        try:
            machines = machine_pool.get_all_machines()
            
            for machine in machines:
                # Skip if machine is already broken or in maintenance
                if machine.is_broken or machine.in_maintenance:
                    continue
                
                # Check if enough time has passed since last breakdown
                machine_key = f"{location}_{machine.machine_id}"
                last_breakdown = self.last_breakdown_times.get(machine_key)
                
                if last_breakdown is not None:
                    time_since_last = datetime.now() - last_breakdown
                    if time_since_last.total_seconds() < (self.config.min_interval_minutes * 60):
                        continue
                
                # Calculate breakdown probability
                if await self._should_trigger_breakdown(machine):
                    await self._trigger_random_breakdown(machine, machine_pool)
                    self.last_breakdown_times[machine_key] = datetime.now()
                    
        except Exception as e:
            logger.error(f"Error checking machines for breakdown in {location}: {e}")
    
    async def _should_trigger_breakdown(self, machine) -> bool:
        """Determine if a machine should have a breakdown"""
        # Base probability per minute check
        probability_per_minute = self.config.breakdown_rate_per_hour / 60
        
        # Adjust probability based on machine usage
        usage_multiplier = 1.0
        if machine.is_busy:
            usage_multiplier = 1.5  # Busy machines more likely to break
        
        # Random check
        return random.random() < (probability_per_minute * usage_multiplier)
    
    async def _trigger_random_breakdown(self, machine, machine_pool):
        """Trigger a random breakdown on a machine"""
        try:
            # Select breakdown type
            breakdown_type = self._select_random_breakdown_type()
            
            # Select breakdown reason
            reasons = self.config.breakdown_reasons.get(breakdown_type, ["Unknown failure"])
            breakdown_reason = random.choice(reasons)
            
            # Select severity
            severity = self._select_random_severity()
            
            # Trigger the breakdown
            machine.trigger_breakdown(breakdown_type, breakdown_reason, severity)
            
            logger.warning(f"Machine breakdown triggered: {machine.machine_id} - {breakdown_type}: {breakdown_reason} ({severity})")
            
            # Call callbacks
            for callback in self.breakdown_callbacks:
                try:
                    await callback(machine, breakdown_type, breakdown_reason, severity)
                except Exception as e:
                    logger.error(f"Error in breakdown callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error triggering breakdown for {machine.machine_id}: {e}")
    
    def _select_random_breakdown_type(self) -> str:
        """Select a random breakdown type based on probabilities"""
        types = list(self.config.breakdown_types.keys())
        weights = list(self.config.breakdown_types.values())
        return random.choices(types, weights=weights)[0]
    
    def _select_random_severity(self) -> str:
        """Select a random severity based on probabilities"""
        severities = list(self.config.severity_distribution.keys())
        weights = list(self.config.severity_distribution.values())
        return random.choices(severities, weights=weights)[0]
    
    def trigger_manual_breakdown(self, machine_id: str, location: str, breakdown_type: str = None, reason: str = None) -> bool:
        """Manually trigger a breakdown on a specific machine"""
        try:
            machine_pool = self.machine_pools.get(location)
            if not machine_pool:
                logger.error(f"No machine pool found for location: {location}")
                return False
            
            machine = machine_pool.get_machine(machine_id)
            if not machine:
                logger.error(f"Machine not found: {machine_id}")
                return False
            
            if machine.is_broken or machine.in_maintenance:
                logger.warning(f"Machine {machine_id} is already broken or in maintenance")
                return False
            
            # Use provided values or generate random ones
            if not breakdown_type:
                breakdown_type = self._select_random_breakdown_type()
            
            if not reason:
                reasons = self.config.breakdown_reasons.get(breakdown_type, ["Manual breakdown triggered"])
                reason = random.choice(reasons)
            
            severity = self._select_random_severity()
            
            # Trigger the breakdown
            machine.trigger_breakdown(breakdown_type, reason, severity)
            
            # Update last breakdown time
            machine_key = f"{location}_{machine_id}"
            self.last_breakdown_times[machine_key] = datetime.now()
            
            logger.info(f"Manual breakdown triggered: {machine_id} - {breakdown_type}: {reason} ({severity})")
            return True
            
        except Exception as e:
            logger.error(f"Error triggering manual breakdown: {e}")
            return False
    
    def reset_machine(self, machine_id: str, location: str) -> bool:
        """Reset a machine from breakdown state"""
        try:
            machine_pool = self.machine_pools.get(location)
            if not machine_pool:
                logger.error(f"No machine pool found for location: {location}")
                return False
            
            machine = machine_pool.get_machine(machine_id)
            if not machine:
                logger.error(f"Machine not found: {machine_id}")
                return False
            
            if not machine.is_broken:
                logger.warning(f"Machine {machine_id} is not in breakdown state")
                return False
            
            machine.reset_breakdown()
            logger.info(f"Machine reset from breakdown: {machine_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting machine breakdown: {e}")
            return False
    
    def reset_all_machines(self) -> int:
        """Reset all machines from breakdown state"""
        reset_count = 0
        try:
            for location, machine_pool in self.machine_pools.items():
                machines = machine_pool.get_all_machines()
                for machine in machines:
                    if machine.is_broken:
                        machine.reset_breakdown()
                        reset_count += 1
            
            logger.info(f"Reset {reset_count} machines from breakdown state")
            return reset_count
            
        except Exception as e:
            logger.error(f"Error resetting all machines: {e}")
            return reset_count
    
    def get_breakdown_stats(self) -> Dict:
        """Get breakdown statistics"""
        total_machines = 0
        broken_machines = 0
        breakdown_by_type = {}
        breakdown_by_severity = {}
        
        try:
            for location, machine_pool in self.machine_pools.items():
                machines = machine_pool.get_all_machines()
                total_machines += len(machines)
                
                for machine in machines:
                    if machine.is_broken:
                        broken_machines += 1
                        
                        # Count by type
                        breakdown_type = machine.breakdown_type or "unknown"
                        breakdown_by_type[breakdown_type] = breakdown_by_type.get(breakdown_type, 0) + 1
                        
                        # Count by severity
                        severity = machine.breakdown_severity
                        breakdown_by_severity[severity] = breakdown_by_severity.get(severity, 0) + 1
            
            return {
                "total_machines": total_machines,
                "broken_machines": broken_machines,
                "operational_machines": total_machines - broken_machines,
                "breakdown_rate": (broken_machines / total_machines * 100) if total_machines > 0 else 0,
                "breakdown_by_type": breakdown_by_type,
                "breakdown_by_severity": breakdown_by_severity,
                "config": {
                    "enabled": self.config.enabled,
                    "rate_per_hour": self.config.breakdown_rate_per_hour
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting breakdown stats: {e}")
            return {"error": str(e)}