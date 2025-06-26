import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from collections import deque
import random
import pytz
from .monitoring import monitor

logger = logging.getLogger(__name__)

class ProductionStage(Enum):
    """Production stages"""
    QUEUED = "queued"
    CNC_MILLING = "cnc_milling"
    LATHE = "lathe"
    ASSEMBLY = "assembly"
    TEST = "test"
    COMPLETED = "completed"

@dataclass
class ProductionLot:
    """In-memory representation of a lot in production"""
    lot_code: str
    customer: str
    quantity: int
    location: str
    priority: str = "normal"
    current_stage: ProductionStage = ProductionStage.QUEUED
    current_machine: Optional[str] = None
    stage_start_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Track production progress
    pieces_produced: int = 0  # How many pieces have been completed so far

    # Track timing for each stage
    cnc_start: Optional[datetime] = None
    cnc_end: Optional[datetime] = None
    lathe_start: Optional[datetime] = None
    lathe_end: Optional[datetime] = None
    assembly_start: Optional[datetime] = None
    assembly_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None

    # Track machine usage for end-of-cycle reporting
    machine_times: Dict[str, float] = field(default_factory=dict)  # machine_id -> time in minutes

    def is_quantity_complete(self) -> bool:
        """Check if the lot has produced all required pieces"""
        return self.pieces_produced >= self.quantity

    def add_pieces_produced(self, count: int = 1):
        """Add to the pieces produced count"""
        self.pieces_produced += count

    def get_remaining_pieces(self) -> int:
        """Get how many pieces still need to be produced"""
        return max(0, self.quantity - self.pieces_produced)

    def get_total_cycle_time(self) -> float:
        """Get total cycle time in minutes"""
        if self.created_at and self.test_end:
            return (self.test_end - self.created_at).total_seconds() / 60
        return 0.0

    def get_stage_time(self, stage: str) -> float:
        """Get time spent in a specific stage in minutes"""
        start_attr = f"{stage}_start"
        end_attr = f"{stage}_end"

        start_time = getattr(self, start_attr, None)
        end_time = getattr(self, end_attr, None)

        if start_time and end_time:
            return (end_time - start_time).total_seconds() / 60
        return 0.0

@dataclass
class Machine:
    """Represents a production machine"""
    machine_id: str
    machine_type: str
    location: str
    is_busy: bool = False
    current_lot: Optional[str] = None
    busy_since: Optional[datetime] = None
    expected_completion: Optional[datetime] = None
    in_maintenance: bool = False
    maintenance_reason: Optional[str] = None
    maintenance_started: Optional[datetime] = None

class ProductionQueue:
    """FIFO queue for each production stage"""
    
    def __init__(self, stage: ProductionStage):
        self.stage = stage
        self.queue: deque[ProductionLot] = deque()
        self.high_priority_queue: deque[ProductionLot] = deque()
    
    def add(self, lot: ProductionLot):
        """Add lot to queue based on priority"""
        if lot.priority == "high":
            self.high_priority_queue.append(lot)
        else:
            self.queue.append(lot)
        logger.debug(f"Added lot {lot.lot_code} to {self.stage.value} queue")
    
    def get_next(self) -> Optional[ProductionLot]:
        """Get next lot from queue (high priority first)"""
        if self.high_priority_queue:
            return self.high_priority_queue.popleft()
        elif self.queue:
            return self.queue.popleft()
        return None
    
    def size(self) -> int:
        """Get total queue size"""
        return len(self.queue) + len(self.high_priority_queue)
    
    def get_lots(self) -> List[ProductionLot]:
        """Get all lots in queue"""
        return list(self.high_priority_queue) + list(self.queue)

class MachinePool:
    """Manages available machines for each type and location"""
    
    def __init__(self):
        self.machines: Dict[str, List[Machine]] = {
            "cnc_milling": [],
            "lathe": [],
            "assembly": [],
            "test": []
        }
        self.all_machines: Dict[str, Machine] = {}
    
    def add_machine(self, machine: Machine):
        """Add a machine to the pool"""
        self.machines[machine.machine_type].append(machine)
        self.all_machines[machine.machine_id] = machine
        logger.info(f"Added machine {machine.machine_id} to pool")
    
    def get_available_machine(self, machine_type: str, location: str) -> Optional[Machine]:
        """Get an available machine of specified type in location"""
        for machine in self.machines.get(machine_type, []):
            if not machine.is_busy and not machine.in_maintenance and machine.location == location:
                return machine
        return None
    
    def assign_lot(self, machine: Machine, lot: ProductionLot, processing_time: int):
        """Assign a lot to a machine"""
        machine.is_busy = True
        machine.current_lot = lot.lot_code
        machine.busy_since = datetime.now()
        machine.expected_completion = datetime.now() + timedelta(seconds=processing_time)
        lot.current_machine = machine.machine_id
        lot.stage_start_time = machine.busy_since
        logger.info(f"Assigned lot {lot.lot_code} to machine {machine.machine_id}")
    
    def free_machine(self, machine_id: str):
        """Free a machine after processing"""
        machine = self.all_machines.get(machine_id)
        if machine:
            machine.is_busy = False
            machine.current_lot = None
            machine.busy_since = None
            machine.expected_completion = None

            # Update machine simulator status
            from .Machine import get_machine_simulator
            simulator = get_machine_simulator(machine_id, machine.machine_type, machine.location)
            if simulator:
                simulator.current_lot = None
                simulator.processing_start_time = None
                simulator.expected_completion_time = None
                simulator.update_status("idle")

            logger.info(f"Freed machine {machine_id}")
    
    def set_machine_maintenance(self, machine_id: str, in_maintenance: bool, reason: str = None):
        """Set machine maintenance status"""
        machine = self.all_machines.get(machine_id)
        if machine:
            machine.in_maintenance = in_maintenance
            if in_maintenance:
                machine.maintenance_reason = reason or "Scheduled maintenance"
                machine.maintenance_started = datetime.now()
                logger.info(f"Machine {machine_id} entered maintenance: {machine.maintenance_reason}")
            else:
                machine.maintenance_reason = None
                machine.maintenance_started = None
                logger.info(f"Machine {machine_id} exited maintenance")

            # Update machine simulator status
            from .Machine import get_machine_simulator
            simulator = get_machine_simulator(machine_id, machine.machine_type, machine.location)
            if simulator:
                if in_maintenance:
                    simulator.update_status("error")
                elif machine.is_busy and machine.current_lot:
                    simulator.update_status("working")
                else:
                    simulator.update_status("idle")
                logger.info(f"Machine {machine_id} exited maintenance")
            return True
        return False

    def get_machines_in_maintenance(self) -> List[Machine]:
        """Get all machines currently in maintenance"""
        return [machine for machine in self.all_machines.values() if machine.in_maintenance]

    def get_machine_status(self) -> Dict[str, Any]:
        """Get status of all machines"""
        status = {}
        for machine_type, machines in self.machines.items():
            status[machine_type] = {
                "total": len(machines),
                "busy": sum(1 for m in machines if m.is_busy),
                "available": sum(1 for m in machines if not m.is_busy and not m.in_maintenance),
                "maintenance": sum(1 for m in machines if m.in_maintenance)
            }
        return status

class ProductionCoordinator:
    """Main coordinator for production flow"""
    
    def __init__(self, kafka_sender):
        self.kafka_sender = kafka_sender
        self.machine_pool = MachinePool()
        self.lots: Dict[str, ProductionLot] = {}

        # Queues for each stage
        self.queues = {
            ProductionStage.QUEUED: ProductionQueue(ProductionStage.QUEUED),
            ProductionStage.CNC_MILLING: ProductionQueue(ProductionStage.CNC_MILLING),
            ProductionStage.LATHE: ProductionQueue(ProductionStage.LATHE),
            ProductionStage.ASSEMBLY: ProductionQueue(ProductionStage.ASSEMBLY),
            ProductionStage.TEST: ProductionQueue(ProductionStage.TEST)
        }

        # High-frequency telemetry tracking
        self.telemetry_enabled = True
        self.telemetry_interval = 1.0  # Send telemetry every 1 second
        
        # Processing time ranges (in seconds) for each stage - ULTRA FAST TESTING MODE
        self.processing_times = {
            "cnc_milling": (8, 12),        # 8-12 seconds (total cycle ~40 seconds)
            "lathe": (8, 12),           # 8-12 seconds (total cycle ~40 seconds)
            "assembly": (8, 12),     # 8-12 seconds (total cycle ~40 seconds)
            "test": (8, 12)              # 8-12 seconds (total cycle ~40 seconds)
        }
        
        # Stage to machine type mapping
        self.stage_to_machine = {
            ProductionStage.QUEUED: "cnc_milling",  # QUEUED lots go to first stage (CNC)
            ProductionStage.CNC_MILLING: "cnc_milling",
            ProductionStage.LATHE: "lathe",
            ProductionStage.ASSEMBLY: "assembly",
            ProductionStage.TEST: "test"
        }
        
        # Running flag
        self.running = False
    
    def initialize_machines(self, config: Dict[str, Dict[str, int]]):
        """Initialize machines based on configuration"""
        for location, machine_counts in config.items():
            for machine_type, count in machine_counts.items():
                # Map config names to internal names
                internal_type = {
                    "cnc_milling": "cnc_milling",
                    "lathe": "lathe",
                    "assembly_line": "assembly",
                    "test_line": "test"
                }.get(machine_type, machine_type)
                
                for i in range(count):
                    machine = Machine(
                        machine_id=f"{internal_type}_{location}_{i+1}",
                        machine_type=internal_type,
                        location=location
                    )
                    self.machine_pool.add_machine(machine)
                    
                    # Add machine to monitoring system so it shows up in web interface
                    monitor.update_machine_status(
                        machine.machine_id, machine.machine_type, machine.location,
                        False, None
                    )
        
        logger.info(f"Initialized machines: {self.machine_pool.get_machine_status()}")
    
    async def add_lot(self, lot_data: Dict[str, Any]):
        """Add a new lot from Kafka message"""
        # Support both old and new field names for backward compatibility
        lot_code = lot_data.get("lot_code") or lot_data.get("codice_lotto")
        customer = lot_data.get("customer") or lot_data.get("cliente")  
        quantity = lot_data.get("quantity") or lot_data.get("quantita")
        priority = lot_data.get("priority") or lot_data.get("priorita", "normal")
        
        lot = ProductionLot(
            lot_code=lot_code,
            customer=customer,
            quantity=quantity,
            location=lot_data["location"],
            priority=priority
        )
        
        self.lots[lot.lot_code] = lot
        self.queues[ProductionStage.QUEUED].add(lot)

        # Update monitoring
        monitor.update_lot_status(
            lot.lot_code, lot.customer, lot.quantity,
            lot.location, "queued", lot.created_at
        )
        monitor.update_queue_status("queued", len(self.queues[ProductionStage.QUEUED].queue))

        # Send event
        await self._send_event("lot.received", {
            "lot_code": lot.lot_code,
            "customer": lot.customer,
            "quantity": lot.quantity,
            "location": lot.location,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Added lot {lot.lot_code} to production queue")
    
    async def process_queues(self):
        """Main processing loop - check queues and assign lots to machines"""
        while self.running:
            try:
                # Process each stage queue
                for stage in [ProductionStage.QUEUED, ProductionStage.CNC_MILLING,
                             ProductionStage.LATHE, ProductionStage.ASSEMBLY, ProductionStage.TEST]:
                    
                    queue = self.queues[stage]
                    if queue.size() == 0:
                        continue
                    
                    # Add debug logging for assembly queue specifically
                    if stage == ProductionStage.ASSEMBLY:
                        logger.info(f"Processing ASSEMBLY queue: {queue.size()} lots waiting")
                        for lot in queue.get_lots():
                            logger.info(f"  - Lot {lot.lot_code} in assembly queue, current_stage: {lot.current_stage}")
                    
                    # Get machine type for this stage
                    machine_type = self.stage_to_machine.get(stage)
                    if not machine_type:
                        continue
                    
                    # Add debug logging for assembly machine availability
                    if stage == ProductionStage.ASSEMBLY:
                        available_machines = [m for m in self.machine_pool.machines.get(machine_type, []) 
                                            if not m.is_busy and not m.in_maintenance]
                        logger.info(f"Available {machine_type} machines: {len(available_machines)}")
                        for m in available_machines:
                            logger.info(f"  - Machine {m.machine_id}, location: {m.location}")
                    
                    # Try to assign lots to available machines
                    lots_to_process = list(queue.get_lots())  # Make a copy to avoid modification during iteration
                    for lot in lots_to_process:
                        machine = self.machine_pool.get_available_machine(
                            machine_type, lot.location
                        )
                        
                        if machine:
                            # Remove from queue using the queue's get_next method
                            removed_lot = queue.get_next()
                            if removed_lot and removed_lot.lot_code == lot.lot_code:
                                # Start processing
                                await self._start_processing(lot, machine, stage)
                            else:
                                # Put it back if we got a different lot
                                if removed_lot:
                                    queue.add(removed_lot)
                
                # Check for completed processing
                await self._check_completed_machines()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in process_queues: {e}")
                await asyncio.sleep(5)
    
    async def _start_processing(self, lot: ProductionLot, machine: Machine, current_stage: ProductionStage):
        """Start processing a lot on a machine"""
        # Calculate processing time
        processing_time = random.randint(*self.processing_times[machine.machine_type])
        
        logger.info(f"Starting processing for lot {lot.lot_code} on machine {machine.machine_id}, from queue stage: {current_stage.value}")
        
        # Assign lot to machine
        self.machine_pool.assign_lot(machine, lot, processing_time)

        # Update lot stage to the processing stage (not the next queue stage)
        processing_stage = self._get_processing_stage(current_stage)
        lot.current_stage = processing_stage
        
        logger.info(f"Lot {lot.lot_code} moved from {current_stage.value} to processing stage: {processing_stage.value}")

        # Update monitoring
        monitor.update_machine_status(
            machine.machine_id, machine.machine_type, machine.location,
            True, lot.lot_code
        )
        monitor.update_lot_status(
            lot.lot_code, lot.customer, lot.quantity,
            lot.location, processing_stage.value
        )
        
        # Update lot timing
        now = datetime.now()
        if processing_stage == ProductionStage.CNC_MILLING:
            lot.cnc_start = now
        elif processing_stage == ProductionStage.LATHE:
            lot.lathe_start = now
        elif processing_stage == ProductionStage.ASSEMBLY:
            lot.assembly_start = now
        elif processing_stage == ProductionStage.TEST:
            lot.test_start = now
        
        # Send telemetry data for machine starting
        await self._send_machine_telemetry(lot, machine, "started")
        
        # Send event
        await self._send_event(f"{machine.machine_type}.started", {
            "lot_code": lot.lot_code,
            "machine_id": machine.machine_id,
            "processing_time_seconds": processing_time,
            "timestamp": now.isoformat()
        })
        
        logger.info(f"Started processing lot {lot.lot_code} on {machine.machine_id}")
    
    async def _check_completed_machines(self):
        """Check for machines that have completed processing"""
        now = datetime.now()
        
        for machine in self.machine_pool.all_machines.values():
            if machine.is_busy and machine.expected_completion and now >= machine.expected_completion:
                # Find the lot
                lot = self.lots.get(machine.current_lot)
                if not lot:
                    continue
                
                # Complete processing
                await self._complete_processing(lot, machine)
    
    async def _complete_processing(self, lot: ProductionLot, machine: Machine):
        """Complete processing for a lot on a machine"""
        now = datetime.now()
        
        logger.info(f"Completing processing for lot {lot.lot_code} on machine {machine.machine_id}, current stage: {lot.current_stage}")
        
        # Update lot timing
        if lot.current_stage == ProductionStage.CNC_MILLING:
            lot.cnc_end = now
        elif lot.current_stage == ProductionStage.LATHE:
            lot.lathe_end = now
        elif lot.current_stage == ProductionStage.ASSEMBLY:
            lot.assembly_end = now
        elif lot.current_stage == ProductionStage.TEST:
            lot.test_end = now
        
        # Send final telemetry for this stage
        await self._send_machine_telemetry(lot, machine, "completed")
        
        # Send event
        await self._send_event(f"{machine.machine_type}.completed", {
            "lot_code": lot.lot_code,
            "machine_id": machine.machine_id,
            "timestamp": now.isoformat()
        })
        
        # Simulate pieces produced during this processing cycle
        # Different machines produce different amounts per cycle
        pieces_per_cycle = self._get_pieces_per_cycle(machine.machine_type)
        remaining_pieces = lot.get_remaining_pieces()
        pieces_produced_this_cycle = min(pieces_per_cycle, remaining_pieces)

        lot.add_pieces_produced(pieces_produced_this_cycle)

        logger.info(f"Lot {lot.lot_code} produced {pieces_produced_this_cycle} pieces on {machine.machine_id}. Progress: {lot.pieces_produced}/{lot.quantity}")

        # Record machine time for this stage
        stage_time = (now - lot.stage_start_time).total_seconds() / 60 if lot.stage_start_time else 0
        lot.machine_times[machine.machine_id] = stage_time

        # Update monitoring for machine becoming free
        monitor.update_machine_status(
            machine.machine_id, machine.machine_type, machine.location,
            False, None
        )

        # Free the machine
        self.machine_pool.free_machine(machine.machine_id)

        # Check if lot quantity is complete for this stage
        if lot.is_quantity_complete():
            # Move to next stage only if all pieces are produced
            next_stage = self._get_next_production_stage(lot.current_stage)
            logger.info(f"Lot {lot.lot_code} completed all {lot.quantity} pieces in {lot.current_stage.value}, moving to: {next_stage.value}")
        else:
            # Stay in current stage to produce more pieces
            next_stage = lot.current_stage
            logger.info(f"Lot {lot.lot_code} needs {lot.get_remaining_pieces()} more pieces, staying in {lot.current_stage.value}")
        
        if next_stage == ProductionStage.COMPLETED:
            # Lot has completed all stages with full quantity
            lot.current_stage = ProductionStage.COMPLETED

            # Record machine time for this stage
            stage_time = (now - lot.stage_start_time).total_seconds() / 60 if lot.stage_start_time else 0
            lot.machine_times[machine.machine_id] = stage_time

            # Send end-of-cycle data
            await self._send_end_of_cycle_data(lot)

            # Update monitoring for completed lot
            monitor.update_lot_status(
                lot.lot_code, lot.customer, lot.quantity,
                lot.location, "completed"
            )
            monitor.complete_lot(lot.lot_code)

            await self._send_event("lot.completed", {
                "lot_code": lot.lot_code,
                "total_time_minutes": (now - lot.created_at).total_seconds() / 60,
                "timestamp": now.isoformat()
            })
            # Remove from active lots
            del self.lots[lot.lot_code]
        elif next_stage == lot.current_stage:
            # Stay in current stage - add back to same queue to produce more pieces
            self.queues[next_stage].add(lot)
            logger.info(f"Added lot {lot.lot_code} back to {next_stage.value} queue for more pieces")
        else:
            # Move to next stage - reset pieces produced for new stage
            lot.current_stage = next_stage
            lot.pieces_produced = 0  # Reset for new stage
            self.queues[next_stage].add(lot)
            logger.info(f"Added lot {lot.lot_code} to {next_stage.value} queue")
        
        logger.info(f"Completed processing lot {lot.lot_code} on {machine.machine_id}")

    def _get_pieces_per_cycle(self, machine_type: str) -> int:
        """Get how many pieces a machine type produces per processing cycle"""
        # Different machine types produce different amounts per cycle
        pieces_per_cycle = {
            "cnc_milling": random.randint(1, 5),    # CNC produces 1-5 pieces per cycle
            "lathe": random.randint(1, 3),          # Lathe produces 1-3 pieces per cycle
            "assembly": random.randint(5, 15),      # Assembly line produces more pieces
            "test": random.randint(1, 8)            # Test line processes multiple pieces
        }
        return pieces_per_cycle.get(machine_type, 1)

    async def _send_machine_telemetry(self, lot: ProductionLot, machine: Machine, status: str):
        """Send machine telemetry data to Kafka"""
        # This will be implemented by the machine simulators
        # Here we just trigger the data generation
        from .Machine import get_machine_simulator

        simulator = get_machine_simulator(machine.machine_id, machine.machine_type, machine.location)
        if simulator:
            # Synchronize simulator state with machine state
            simulator.current_lot = lot.lot_code
            simulator.processing_start_time = machine.busy_since
            simulator.expected_completion_time = machine.expected_completion

            # Update simulator status based on machine state
            if machine.in_maintenance:
                simulator.update_status("error")
            elif machine.is_busy and machine.current_lot:
                simulator.update_status("working")
            else:
                simulator.update_status("idle")

            # Clear manual override since this is automatic state sync
            simulator._manual_status_override = False

            # Send regular telemetry data
            data = simulator.generate_data()
            data["status"] = status
            await self.kafka_sender.send_to_kafka(data)

            # Send telemetry data
            telemetry_data = simulator.generate_measurement_data()
            await self.kafka_sender.send_telemetry_data(telemetry_data, machine.machine_type)

    async def _send_end_of_cycle_data(self, lot: ProductionLot):
        """Send production completion data for the completed lot"""
        from .models import ProductionCompletionData, Location

        # Get timestamps
        utc_now = datetime.now(pytz.UTC)

        # Map location string to Location enum
        location_map = {
            "Italy": Location.ITALY,
            "Brazil": Location.BRAZIL,
            "Vietnam": Location.VIETNAM
        }

        location_enum = location_map.get(lot.location, Location.ITALY)
        local_tz = pytz.timezone(location_enum.value[1])
        local_now = utc_now.astimezone(local_tz)

        # Map location to site name
        site_mapping = {
            "Italy": "Italy",
            "Brazil": "Brazil",
            "Vietnam": "Vietnam"
        }
        site = site_mapping.get(lot.location, "Italy")

        # Calculate stage durations in minutes
        cnc_duration = int(lot.get_stage_time("cnc"))
        lathe_duration = int(lot.get_stage_time("lathe"))
        assembly_duration = int(lot.get_stage_time("assembly"))
        test_duration = int(lot.get_stage_time("test"))
        total_duration_minutes = cnc_duration + lathe_duration + assembly_duration + test_duration

        production_completion_data = ProductionCompletionData(
            lot_code=lot.lot_code,
            customer=lot.customer,
            quantity=lot.quantity,
            site=site,
            local_timestamp=local_now.isoformat(),
            completion_timestamp=utc_now.isoformat(),
            total_duration_minutes=total_duration_minutes,
            cnc_duration=cnc_duration,
            lathe_duration=lathe_duration,
            assembly_duration=assembly_duration,
            test_duration=test_duration,
            result="COMPLETED"  # Assuming all lots complete successfully for now
        )

        # Convert to dict and send
        from dataclasses import asdict
        completion_data = asdict(production_completion_data)
        await self.kafka_sender.send_production_completion_data(completion_data)
    
    async def _send_event(self, event_type: str, data: Dict[str, Any]):
        """Send production event to Kafka"""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to events topic
        await self.kafka_sender.kafka_producer.send_and_wait(
            topic="coffeemek.events.production_status",
            key=data.get("lot_code", ""),
            value=event
        )
    
    def _get_next_stage(self, current_stage: ProductionStage) -> ProductionStage:
        """Get the next processing stage (for starting)"""
        transitions = {
            ProductionStage.QUEUED: ProductionStage.CNC_MILLING,
            ProductionStage.CNC_MILLING: ProductionStage.LATHE,
            ProductionStage.LATHE: ProductionStage.ASSEMBLY,
            ProductionStage.ASSEMBLY: ProductionStage.TEST
        }
        return transitions.get(current_stage, current_stage)
    
    def _get_processing_stage(self, queue_stage: ProductionStage) -> ProductionStage:
        """Get the processing stage for a given queue stage"""
        transitions = {
            ProductionStage.QUEUED: ProductionStage.CNC_MILLING,
            ProductionStage.CNC_MILLING: ProductionStage.CNC_MILLING,
            ProductionStage.LATHE: ProductionStage.LATHE,
            ProductionStage.ASSEMBLY: ProductionStage.ASSEMBLY,
            ProductionStage.TEST: ProductionStage.TEST
        }
        return transitions.get(queue_stage, queue_stage)
    
    def _get_next_production_stage(self, current_stage: ProductionStage) -> ProductionStage:
        """Get the next queue stage (after completion)"""
        transitions = {
            ProductionStage.CNC_MILLING: ProductionStage.LATHE,
            ProductionStage.LATHE: ProductionStage.ASSEMBLY,
            ProductionStage.ASSEMBLY: ProductionStage.TEST,
            ProductionStage.TEST: ProductionStage.COMPLETED
        }
        return transitions.get(current_stage, ProductionStage.COMPLETED)
    
    async def start(self):
        """Start the production coordinator"""
        self.running = True
        monitor.start()
        logger.info("Production coordinator started")

        # Start all concurrent tasks
        await asyncio.gather(
            self.process_queues(),
            self._high_frequency_telemetry_loop(),
            self._random_maintenance_events()
        )
    
    async def _high_frequency_telemetry_loop(self):
        """Send telemetry data every second for active machines"""
        while self.running:
            try:
                if self.telemetry_enabled:
                    # Send telemetry for all busy machines
                    for machine in self.machine_pool.all_machines.values():
                        if machine.is_busy and machine.current_lot:
                            # Find the lot being processed
                            lot = self.lots.get(machine.current_lot)
                            if lot:
                                await self._send_machine_telemetry(lot, machine, "processing")

                # Wait for next telemetry interval
                await asyncio.sleep(self.telemetry_interval)

            except Exception as e:
                logger.error(f"Error in high-frequency telemetry loop: {e}")
                await asyncio.sleep(1)  # Continue after error

    async def stop(self):
        """Stop the production coordinator"""
        self.running = False
        await monitor.stop()
        logger.info("Production coordinator stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current production status"""
        status = {
            "active_lots": len(self.lots),
            "queues": {},
            "machines": self.machine_pool.get_machine_status()
        }
        
        for stage, queue in self.queues.items():
            status["queues"][stage.value] = {
                "size": queue.size(),
                "lots": [lot.lot_code for lot in queue.get_lots()]
            }
        
        return status

    async def _process_single_queue_iteration(self):
        """Process queues for a single iteration (used for manual triggering)"""
        try:
            # Process each stage queue
            for stage in [ProductionStage.QUEUED, ProductionStage.CNC_MILLING,
                         ProductionStage.LATHE, ProductionStage.ASSEMBLY, ProductionStage.TEST]:
                
                queue = self.queues[stage]
                if queue.size() == 0:
                    continue
                
                # Get machine type for this stage
                machine_type = self.stage_to_machine.get(stage)
                if not machine_type:
                    continue
                
                # Try to assign lots to available machines
                lots_to_process = list(queue.get_lots())  # Make a copy to avoid modification during iteration
                for lot in lots_to_process:
                    machine = self.machine_pool.get_available_machine(
                        machine_type, lot.location
                    )
                    
                    if machine:
                        # Remove from queue using the queue's get_next method
                        removed_lot = queue.get_next()
                        if removed_lot and removed_lot.lot_code == lot.lot_code:
                            # Start processing
                            await self._start_processing(lot, machine, stage)
                        else:
                            # Put it back if we got a different lot
                            if removed_lot:
                                queue.add(removed_lot)
            
            # Check for completed processing
            await self._check_completed_machines()
            
        except Exception as e:
            logger.error(f"Error in manual queue processing: {e}")

    def set_machine_maintenance(self, machine_id: str, in_maintenance: bool, reason: str = None) -> bool:
        """Set machine maintenance status"""
        return self.machine_pool.set_machine_maintenance(machine_id, in_maintenance, reason)

    def get_all_machines(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all machines"""
        machines_info = {}
        for machine_id, machine in self.machine_pool.all_machines.items():
            machines_info[machine_id] = {
                "machine_id": machine.machine_id,
                "machine_type": machine.machine_type,
                "location": machine.location,
                "is_busy": machine.is_busy,
                "current_lot": machine.current_lot,
                "in_maintenance": machine.in_maintenance,
                "maintenance_reason": machine.maintenance_reason,
                "maintenance_started": machine.maintenance_started.isoformat() if machine.maintenance_started else None,
                "expected_completion": machine.expected_completion.isoformat() if machine.expected_completion else None
            }
        return machines_info

    async def _random_maintenance_events(self):
        """Randomly trigger maintenance events on machines"""
        while self.running:
            try:
                # Check every 5 minutes for potential maintenance events
                await asyncio.sleep(300)
                
                # 10% chance per check that a random machine goes into maintenance
                if random.random() < 0.1:
                    available_machines = [
                        machine for machine in self.machine_pool.all_machines.values()
                        if not machine.is_busy and not machine.in_maintenance
                    ]
                    
                    if available_machines:
                        machine = random.choice(available_machines)
                        reasons = [
                            "Scheduled maintenance",
                            "Preventive maintenance", 
                            "Component replacement",
                            "Calibration required",
                            "Safety inspection"
                        ]
                        reason = random.choice(reasons)
                        
                        self.set_machine_maintenance(machine.machine_id, True, reason)
                        
                        # Send event
                        await self._send_event("machine.maintenance.started", {
                            "machine_id": machine.machine_id,
                            "machine_type": machine.machine_type,
                            "location": machine.location,
                            "reason": reason,
                            "timestamp": datetime.now().isoformat()
                        })

            except Exception as e:
                logger.error(f"Error in random maintenance events: {e}")
                await asyncio.sleep(60)