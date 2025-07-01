import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from collections import deque
import random
import pytz
from .monitoring import monitor
from .database import ProductionDatabase

logger = logging.getLogger(__name__)

class ProductionStage(Enum):
    """Production stages"""
    QUEUED = "queued"
    CNC = "cnc"
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
    pieces_in_production: Dict[str, 'ProductionPiece'] = field(default_factory=dict)  # piece_id -> piece

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

    def create_pieces(self) -> List['ProductionPiece']:
        """Create individual pieces for this lot"""
        pieces = []
        for piece_num in range(1, self.quantity + 1):
            piece_id = f"{self.lot_code}_P{piece_num:03d}"
            piece = ProductionPiece(
                piece_id=piece_id,
                lot_code=self.lot_code,
                piece_number=piece_num,
                customer=self.customer,
                location=self.location,
                priority=self.priority
            )
            pieces.append(piece)
            self.pieces_in_production[piece_id] = piece
        return pieces

    def get_pieces_in_stage(self, stage: ProductionStage) -> List['ProductionPiece']:
        """Get all pieces currently in a specific stage"""
        return [piece for piece in self.pieces_in_production.values()
                if piece.current_stage == stage]

    def get_completed_pieces(self) -> List['ProductionPiece']:
        """Get all pieces that have completed production"""
        return [piece for piece in self.pieces_in_production.values()
                if piece.is_completed()]

    def is_lot_complete(self) -> bool:
        """Check if all pieces in the lot have completed production"""
        return len(self.get_completed_pieces()) == self.quantity

    def get_lot_progress(self) -> Dict[str, int]:
        """Get count of pieces in each stage"""
        progress = {stage.value: 0 for stage in ProductionStage}
        for piece in self.pieces_in_production.values():
            progress[piece.current_stage.value] += 1
        return progress

    def get_total_cycle_time(self) -> float:
        """Get total cycle time in minutes"""
        if self.created_at and self.test_end:
            return (self.test_end - self.created_at).total_seconds() / 60
        return 0.0


@dataclass
class ProductionPiece:
    """Individual piece moving through the production pipeline"""
    piece_id: str  # Unique identifier for this piece (lot_code + piece_number)
    lot_code: str  # Parent lot identifier
    piece_number: int  # Piece number within the lot (1, 2, 3, ...)
    customer: str  # Customer name (inherited from lot)
    location: str  # Production location (inherited from lot)
    priority: str = "normal"  # Priority (inherited from lot)

    # Current state
    current_stage: ProductionStage = ProductionStage.QUEUED
    current_machine: Optional[str] = None
    stage_start_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Track timing for each stage
    cnc_start: Optional[datetime] = None
    cnc_end: Optional[datetime] = None
    lathe_start: Optional[datetime] = None
    lathe_end: Optional[datetime] = None
    assembly_start: Optional[datetime] = None
    assembly_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None

    def is_completed(self) -> bool:
        """Check if this piece has completed all production stages"""
        return self.current_stage == ProductionStage.COMPLETED

    def get_stage_duration(self, stage: ProductionStage) -> float:
        """Get duration in minutes for a specific stage"""
        stage_times = {
            ProductionStage.CNC: (self.cnc_start, self.cnc_end),
            ProductionStage.LATHE: (self.lathe_start, self.lathe_end),
            ProductionStage.ASSEMBLY: (self.assembly_start, self.assembly_end),
            ProductionStage.TEST: (self.test_start, self.test_end)
        }

        start_time, end_time = stage_times.get(stage, (None, None))
        if start_time and end_time:
            return (end_time - start_time).total_seconds() / 60
        return 0.0

    def get_total_cycle_time(self) -> float:
        """Get total cycle time in minutes for this piece"""
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
    current_piece: Optional[str] = None  # piece_id instead of lot_code
    current_lot: Optional[str] = None    # Keep for compatibility and tracking
    busy_since: Optional[datetime] = None
    expected_completion: Optional[datetime] = None
    in_maintenance: bool = False
    maintenance_reason: Optional[str] = None
    maintenance_started: Optional[datetime] = None
    
    # Machine breakdown fields
    is_broken: bool = False
    breakdown_type: Optional[str] = None
    breakdown_reason: Optional[str] = None
    breakdown_start_time: Optional[datetime] = None
    breakdown_severity: str = "minor"  # minor, major, critical
    
    def get_status(self) -> str:
        """Get machine status for display"""
        if self.is_broken:
            return "error"
        elif self.in_maintenance:
            return "maintenance"
        elif self.is_busy:
            return "running"
        else:
            return "idle"
    
    def trigger_breakdown(self, breakdown_type: str, reason: str, severity: str = "minor"):
        """Trigger a machine breakdown"""
        self.is_broken = True
        self.breakdown_type = breakdown_type
        self.breakdown_reason = reason
        self.breakdown_start_time = datetime.now()
        self.breakdown_severity = severity
        
        # If machine was busy, stop the current operation
        if self.is_busy:
            self.is_busy = False
            self.current_piece = None
            self.current_lot = None
            self.busy_since = None
            self.expected_completion = None
    
    def reset_breakdown(self):
        """Reset machine from breakdown state"""
        self.is_broken = False
        self.breakdown_type = None
        self.breakdown_reason = None
        self.breakdown_start_time = None
        self.breakdown_severity = "minor"
    
    def get_breakdown_duration_minutes(self) -> float:
        """Get breakdown duration in minutes"""
        if self.breakdown_start_time:
            return (datetime.now() - self.breakdown_start_time).total_seconds() / 60
        return 0.0

class ProductionQueue:
    """FIFO queue for each production stage - now handles individual pieces with thread safety"""

    def __init__(self, stage: ProductionStage):
        self.stage = stage
        self.queue: deque[ProductionPiece] = deque()
        self.high_priority_queue: deque[ProductionPiece] = deque()
        self._lock = asyncio.Lock()  # Add async lock for concurrent access

    async def add(self, piece: ProductionPiece):
        """Add piece to queue based on priority (thread-safe)"""
        async with self._lock:
            if piece.priority == "high":
                self.high_priority_queue.append(piece)
            else:
                self.queue.append(piece)
            logger.debug(f"Added piece {piece.piece_id} to {self.stage.value} queue")

    async def get_next(self) -> Optional[ProductionPiece]:
        """Get next piece from queue (high priority first, thread-safe)"""
        async with self._lock:
            if self.high_priority_queue:
                return self.high_priority_queue.popleft()
            elif self.queue:
                return self.queue.popleft()
            return None

    async def size(self) -> int:
        """Get total queue size (thread-safe)"""
        async with self._lock:
            return len(self.queue) + len(self.high_priority_queue)

    async def get_pieces(self) -> List[ProductionPiece]:
        """Get all pieces in queue (thread-safe)"""
        async with self._lock:
            return list(self.high_priority_queue) + list(self.queue)

    async def get_lots_in_queue(self) -> Set[str]:
        """Get unique lot codes that have pieces in this queue (thread-safe)"""
        async with self._lock:
            lot_codes = set()
            for piece in list(self.high_priority_queue) + list(self.queue):
                lot_codes.add(piece.lot_code)
            return lot_codes

    async def remove_specific_piece(self, piece_id: str) -> Optional[ProductionPiece]:
        """Remove a specific piece from the queue by piece_id (thread-safe)"""
        async with self._lock:
            # Check high priority queue first
            for i, piece in enumerate(self.high_priority_queue):
                if piece.piece_id == piece_id:
                    if i == 0:
                        return self.high_priority_queue.popleft()
                    else:
                        # Remove from middle of queue
                        temp_pieces = []
                        found_piece = None
                        for _ in range(i):
                            temp_pieces.append(self.high_priority_queue.popleft())
                        if self.high_priority_queue:
                            found_piece = self.high_priority_queue.popleft()
                        # Put back the pieces we removed
                        for temp_piece in reversed(temp_pieces):
                            self.high_priority_queue.appendleft(temp_piece)
                        return found_piece

            # Check regular queue
            for i, piece in enumerate(self.queue):
                if piece.piece_id == piece_id:
                    if i == 0:
                        return self.queue.popleft()
                    else:
                        # Remove from middle of queue
                        temp_pieces = []
                        found_piece = None
                        for _ in range(i):
                            temp_pieces.append(self.queue.popleft())
                        if self.queue:
                            found_piece = self.queue.popleft()
                        # Put back the pieces we removed
                        for temp_piece in reversed(temp_pieces):
                            self.queue.appendleft(temp_piece)
                        return found_piece

            return None

    async def clear_all(self):
        """Clear all pieces from the queue (thread-safe)"""
        async with self._lock:
            cleared_count = len(self.queue) + len(self.high_priority_queue)
            self.queue.clear()
            self.high_priority_queue.clear()
            logger.info(f"Cleared {cleared_count} pieces from {self.stage.value} queue")
            return cleared_count

class MachinePool:
    """Manages available machines for each type and location with thread safety"""

    def __init__(self):
        self.machines: Dict[str, List[Machine]] = {
            "cnc": [],
            "lathe": [],
            "assembly": [],
            "test": []
        }
        self.all_machines: Dict[str, Machine] = {}
        self._lock = asyncio.Lock()  # Add async lock for concurrent access

    async def add_machine(self, machine: Machine):
        """Add a machine to the pool (thread-safe)"""
        async with self._lock:
            self.machines[machine.machine_type].append(machine)
            self.all_machines[machine.machine_id] = machine
            logger.info(f"Added machine {machine.machine_id} to pool")

    async def get_available_machine(self, machine_type: str, location: str) -> Optional[Machine]:
        """Get an available machine of specified type in location (thread-safe)"""
        async with self._lock:
            for machine in self.machines.get(machine_type, []):
                if not machine.is_busy and not machine.in_maintenance and not machine.is_broken and machine.location == location:
                    return machine
            return None

    async def assign_piece(self, machine: Machine, piece: ProductionPiece, processing_time: int):
        """Assign a piece to a machine (thread-safe)"""
        async with self._lock:
            machine.is_busy = True
            machine.current_piece = piece.piece_id
            machine.current_lot = piece.lot_code  # Keep for compatibility
            machine.busy_since = datetime.now()
            machine.expected_completion = datetime.now() + timedelta(seconds=processing_time)
            piece.current_machine = machine.machine_id
            piece.stage_start_time = machine.busy_since
            logger.info(f"Assigned piece {piece.piece_id} (lot {piece.lot_code}) to machine {machine.machine_id}")

    async def assign_lot(self, machine: Machine, lot: ProductionLot, processing_time: int):
        """Legacy method - kept for compatibility (thread-safe)"""
        # This method is deprecated but kept for any remaining legacy code
        async with self._lock:
            machine.is_busy = True
            machine.current_lot = lot.lot_code
            machine.busy_since = datetime.now()
            machine.expected_completion = datetime.now() + timedelta(seconds=processing_time)
            lot.current_machine = machine.machine_id
            lot.stage_start_time = machine.busy_since
            logger.info(f"Assigned lot {lot.lot_code} to machine {machine.machine_id}")

    async def free_machine(self, machine_id: str):
        """Free a machine after processing (thread-safe)"""
        async with self._lock:
            machine = self.all_machines.get(machine_id)
            if machine:
                machine.is_busy = False
                machine.current_piece = None
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

    async def set_machine_maintenance(self, machine_id: str, in_maintenance: bool, reason: str = None):
        """Set machine maintenance status (thread-safe)"""
        async with self._lock:
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
    
    async def trigger_machine_breakdown(self, machine_id: str, breakdown_type: str = None, reason: str = None, severity: str = "minor"):
        """Trigger a breakdown on a specific machine (thread-safe)"""
        async with self._lock:
            machine = self.all_machines.get(machine_id)
            if machine and not machine.is_broken and not machine.in_maintenance:
                machine.trigger_breakdown(breakdown_type or "mechanical", reason or "Manual breakdown", severity)
                
                # Update machine simulator status
                from .Machine import get_machine_simulator
                simulator = get_machine_simulator(machine_id, machine.machine_type, machine.location)
                if simulator:
                    simulator.update_status("error")
                
                logger.warning(f"Machine {machine_id} breakdown triggered: {machine.breakdown_type} - {machine.breakdown_reason}")
                return True
            return False
    
    async def reset_machine_breakdown(self, machine_id: str):
        """Reset a machine from breakdown state (thread-safe)"""
        async with self._lock:
            machine = self.all_machines.get(machine_id)
            if machine and machine.is_broken:
                machine.reset_breakdown()
                
                # Update machine simulator status
                from .Machine import get_machine_simulator
                simulator = get_machine_simulator(machine_id, machine.machine_type, machine.location)
                if simulator:
                    if machine.is_busy and machine.current_lot:
                        simulator.update_status("working")
                    else:
                        simulator.update_status("idle")
                
                logger.info(f"Machine {machine_id} reset from breakdown")
                return True
            return False
    
    async def reset_all_machine_breakdowns(self):
        """Reset all machines from breakdown state (thread-safe)"""
        async with self._lock:
            reset_count = 0
            for machine in self.all_machines.values():
                if machine.is_broken:
                    machine.reset_breakdown()
                    reset_count += 1
                    
                    # Update machine simulator status
                    from .Machine import get_machine_simulator
                    simulator = get_machine_simulator(machine.machine_id, machine.machine_type, machine.location)
                    if simulator:
                        if machine.is_busy and machine.current_lot:
                            simulator.update_status("working")
                        else:
                            simulator.update_status("idle")
            
            logger.info(f"Reset {reset_count} machines from breakdown state")
            return reset_count
    
    def get_broken_machines(self) -> List[Machine]:
        """Get all machines currently broken"""
        return [machine for machine in self.all_machines.values() if machine.is_broken]
    
    def get_machine(self, machine_id: str) -> Optional[Machine]:
        """Get a specific machine by ID"""
        return self.all_machines.get(machine_id)
    
    def get_all_machines(self) -> List[Machine]:
        """Get all machines in the pool"""
        return list(self.all_machines.values())

    def get_machine_status(self) -> Dict[str, Any]:
        """Get status of all machines"""
        status = {}
        for machine_type, machines in self.machines.items():
            status[machine_type] = {
                "total": len(machines),
                "busy": sum(1 for m in machines if m.is_busy),
                "available": sum(1 for m in machines if not m.is_busy and not m.in_maintenance and not m.is_broken),
                "maintenance": sum(1 for m in machines if m.in_maintenance),
                "broken": sum(1 for m in machines if m.is_broken)
            }
        return status

class ProductionCoordinator:
    """Main coordinator for production flow"""
    
    def __init__(self, kafka_sender):
        self.kafka_sender = kafka_sender
        self.machine_pool = MachinePool()
        self.lots: Dict[str, ProductionLot] = {}
        
        # Initialize database
        self.db = ProductionDatabase()

        # Queues for each stage
        self.queues = {
            ProductionStage.QUEUED: ProductionQueue(ProductionStage.QUEUED),
            ProductionStage.CNC: ProductionQueue(ProductionStage.CNC),
            ProductionStage.LATHE: ProductionQueue(ProductionStage.LATHE),
            ProductionStage.ASSEMBLY: ProductionQueue(ProductionStage.ASSEMBLY),
            ProductionStage.TEST: ProductionQueue(ProductionStage.TEST)
        }

        # High-frequency telemetry tracking
        self.telemetry_enabled = True
        self.telemetry_interval = 5.0  # Send telemetry every 5 seconds
        
        # Processing time ranges (in seconds) for each stage - ULTRA FAST TESTING MODE
        self.processing_times = {
            "cnc": (8, 12),        # 8-12 seconds (total cycle ~40 seconds)
            "lathe": (8, 12),           # 8-12 seconds (total cycle ~40 seconds)
            "assembly": (8, 12),     # 8-12 seconds (total cycle ~40 seconds)
            "test": (8, 12)              # 8-12 seconds (total cycle ~40 seconds)
        }
        
        # Stage to machine type mapping
        self.stage_to_machine = {
            ProductionStage.QUEUED: "cnc",  # QUEUED lots go to first stage (CNC)
            ProductionStage.CNC: "cnc",
            ProductionStage.LATHE: "lathe",
            ProductionStage.ASSEMBLY: "assembly",
            ProductionStage.TEST: "test"
        }
        
        # Running flag
        self.running = False
    
    async def initialize_machines(self, config: Dict[str, Dict[str, int]]):
        """Initialize machines based on configuration"""
        for location, machine_counts in config.items():
            for machine_type, count in machine_counts.items():
                # Map config names to internal names
                internal_type = {
                    "cnc": "cnc",
                    "lathe": "lathe",
                    "assembly_line": "assembly",
                    "test_line": "test"
                }.get(machine_type, machine_type)
                
                for i in range(count):
                    # Create machine_id in format: {type}_{site}
                    site_mapping = {
                        "Italy": "italy",
                        "Brazil": "brazil", 
                        "Vietnam": "vietnam"
                    }
                    site = site_mapping.get(location, location.lower())
                    
                    # Format: {type}_{site} (e.g., cnc_italy, lathe_brazil)
                    machine_id = f"{internal_type}_{site}"
                    
                    machine = Machine(
                        machine_id=machine_id,
                        machine_type=internal_type,
                        location=location
                    )
                    await self.machine_pool.add_machine(machine)
                    
                    # Add machine to monitoring system so it shows up in web interface
                    monitor.update_machine_status(
                        machine.machine_id, machine.machine_type, machine.location,
                        False, None
                    )
        
        logger.info(f"Initialized machines: {self.machine_pool.get_machine_status()}")
    
    async def add_lot(self, lot_data: Dict[str, Any]):
        """Add a new lot from Kafka message"""
        # First save to database - this creates lot and pieces atomically
        success = await self.db.add_lot(lot_data)
        if not success:
            logger.error(f"Failed to save lot to database: {lot_data}")
            return
        
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

        # Create individual pieces for this lot
        pieces = lot.create_pieces()

        # Add lot to in-memory tracking
        self.lots[lot.lot_code] = lot

        # Add each piece to the initial queue (in-memory for processing)
        for piece in pieces:
            await self.queues[ProductionStage.QUEUED].add(piece)

        logger.info(f"Added lot {lot_code} to database and created {len(pieces)} pieces for processing")

        # Update monitoring
        monitor.update_lot_status(
            lot.lot_code, lot.customer, lot.quantity,
            lot.location, "queued", lot.created_at
        )
        queue_size = await self.queues[ProductionStage.QUEUED].size()
        monitor.update_queue_status("queued", queue_size)


        logger.info(f"Added lot {lot.lot_code} to production queue")
    
    async def process_queues_for_location(self, location: str):
        """Location-specific processing loop - check queues and assign pieces to machines for a specific location"""
        logger.info(f"Starting concurrent processing for location: {location}")

        while self.running:
            try:
                # Process each stage queue for this location only
                for stage in [ProductionStage.QUEUED, ProductionStage.CNC,
                             ProductionStage.LATHE, ProductionStage.ASSEMBLY, ProductionStage.TEST]:

                    queue = self.queues[stage]
                    queue_size = await queue.size()
                    if queue_size == 0:
                        continue

                    # Get machine type for this stage
                    machine_type = self.stage_to_machine.get(stage)
                    if not machine_type:
                        continue

                    # Try to assign pieces to available machines for this location
                    pieces_to_process = await queue.get_pieces()  # Get all pieces in queue
                    location_pieces = [piece for piece in pieces_to_process if piece.location == location]

                    if location_pieces:
                        logger.debug(f"Location {location} processing {stage.value} queue: {len(location_pieces)} pieces")

                    for piece in location_pieces:
                        machine = await self.machine_pool.get_available_machine(
                            machine_type, piece.location
                        )

                        if machine:
                            # Remove the specific piece from queue
                            removed_piece = await queue.remove_specific_piece(piece.piece_id)
                            if removed_piece:
                                # Start processing
                                await self._start_processing_piece(piece, machine, stage)

                # Check for completed processing for this location
                await self._check_completed_machines_for_location(location)

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.5)  # Reduced delay for better responsiveness

            except Exception as e:
                logger.error(f"Error in process_queues for location {location}: {e}")
                await asyncio.sleep(5)



    async def _check_completed_machines_for_location(self, location: str):
        """Check for machines that have completed processing for a specific location"""
        now = datetime.now()

        for machine in self.machine_pool.all_machines.values():
            # Only check machines for this location
            if machine.location != location:
                continue

            if machine.is_busy and machine.expected_completion and now >= machine.expected_completion:
                # Find the piece being processed
                piece = None
                if machine.current_piece:
                    # Find the piece in the lot's pieces
                    lot = self.lots.get(machine.current_lot)
                    if lot and machine.current_piece in lot.pieces_in_production:
                        piece = lot.pieces_in_production[machine.current_piece]

                if piece:
                    # Complete processing for the piece
                    await self._complete_processing_piece(piece, machine)
                elif machine.current_lot:
                    # Fallback to legacy lot processing if no piece found
                    lot = self.lots.get(machine.current_lot)
                    if lot:
                        await self._complete_processing(lot, machine)
    
    async def _start_processing(self, lot: ProductionLot, machine: Machine, current_stage: ProductionStage):
        """Start processing a lot on a machine"""
        # Calculate processing time
        processing_time = random.randint(*self.processing_times[machine.machine_type])
        
        logger.info(f"Starting processing for lot {lot.lot_code} on machine {machine.machine_id}, from queue stage: {current_stage.value}")
        
        # Assign lot to machine
        await self.machine_pool.assign_lot(machine, lot, processing_time)

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
        if processing_stage == ProductionStage.CNC:
            lot.cnc_start = now
        elif processing_stage == ProductionStage.LATHE:
            lot.lathe_start = now
        elif processing_stage == ProductionStage.ASSEMBLY:
            lot.assembly_start = now
        elif processing_stage == ProductionStage.TEST:
            lot.test_start = now
        
        # Send telemetry data for machine starting
        await self._send_machine_telemetry(lot, machine, "started")
        
        
        logger.info(f"Started processing lot {lot.lot_code} on {machine.machine_id}")

    async def _start_processing_piece(self, piece: ProductionPiece, machine: Machine, current_stage: ProductionStage):
        """Start processing a piece on a machine"""
        # Calculate processing time
        processing_time = random.randint(*self.processing_times[machine.machine_type])

        logger.info(f"Starting processing for piece {piece.piece_id} (lot {piece.lot_code}) on machine {machine.machine_id}, from queue stage: {current_stage.value}")

        # Assign piece to machine
        await self.machine_pool.assign_piece(machine, piece, processing_time)

        # Update piece stage to the processing stage (not the next queue stage)
        processing_stage = self._get_processing_stage(current_stage)
        piece.current_stage = processing_stage

        logger.info(f"Piece {piece.piece_id} moved from {current_stage.value} to processing stage: {processing_stage.value}")

        # Update monitoring
        monitor.update_machine_status(
            machine.machine_id, machine.machine_type, machine.location,
            True, piece.lot_code
        )

        # Update piece timing
        now = datetime.now()
        if processing_stage == ProductionStage.CNC:
            piece.cnc_start = now
        elif processing_stage == ProductionStage.LATHE:
            piece.lathe_start = now
        elif processing_stage == ProductionStage.ASSEMBLY:
            piece.assembly_start = now
        elif processing_stage == ProductionStage.TEST:
            piece.test_start = now

        # Send telemetry data for machine starting
        # await self._send_piece_telemetry(piece, machine, "started")  # Commented out to reduce message frequency


        logger.info(f"Started processing piece {piece.piece_id} on {machine.machine_id}")

    async def _check_completed_machines(self):
        """Check for machines that have completed processing"""
        now = datetime.now()

        for machine in self.machine_pool.all_machines.values():
            if machine.is_busy and machine.expected_completion and now >= machine.expected_completion:
                # Find the piece being processed
                piece = None
                if machine.current_piece:
                    # Find the piece in the lot's pieces
                    lot = self.lots.get(machine.current_lot)
                    if lot and machine.current_piece in lot.pieces_in_production:
                        piece = lot.pieces_in_production[machine.current_piece]

                if piece:
                    # Complete processing for the piece
                    await self._complete_processing_piece(piece, machine)
                elif machine.current_lot:
                    # Fallback to legacy lot processing if no piece found
                    lot = self.lots.get(machine.current_lot)
                    if lot:
                        await self._complete_processing(lot, machine)
    
    async def _complete_processing(self, lot: ProductionLot, machine: Machine):
        """Complete processing for a lot on a machine"""
        now = datetime.now()
        
        logger.info(f"Completing processing for lot {lot.lot_code} on machine {machine.machine_id}, current stage: {lot.current_stage}")
        
        # Update lot timing
        if lot.current_stage == ProductionStage.CNC:
            lot.cnc_end = now
        elif lot.current_stage == ProductionStage.LATHE:
            lot.lathe_end = now
        elif lot.current_stage == ProductionStage.ASSEMBLY:
            lot.assembly_end = now
        elif lot.current_stage == ProductionStage.TEST:
            lot.test_end = now
        
        # Send final telemetry for this stage
        await self._send_machine_telemetry(lot, machine, "completed")
        
        
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
        await self.machine_pool.free_machine(machine.machine_id)

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

            # NOTE: No longer sending lot-level completion data - using piece-by-piece completion

            # Update monitoring for completed lot
            monitor.update_lot_status(
                lot.lot_code, lot.customer, lot.quantity,
                lot.location, "completed"
            )
            monitor.complete_lot(lot.lot_code)

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

    async def _complete_processing_piece(self, piece: ProductionPiece, machine: Machine):
        """Complete processing for a piece on a machine"""
        now = datetime.now()

        logger.info(f"Completing processing for piece {piece.piece_id} (lot {piece.lot_code}) on machine {machine.machine_id}, current stage: {piece.current_stage}")

        # Update piece timing
        if piece.current_stage == ProductionStage.CNC:
            piece.cnc_end = now
        elif piece.current_stage == ProductionStage.LATHE:
            piece.lathe_end = now
        elif piece.current_stage == ProductionStage.ASSEMBLY:
            piece.assembly_end = now
        elif piece.current_stage == ProductionStage.TEST:
            piece.test_end = now

        # Send final telemetry for this stage
        # await self._send_piece_telemetry(piece, machine, "completed")  # Commented out to reduce message frequency


        # Update monitoring for machine becoming free
        monitor.update_machine_status(
            machine.machine_id, machine.machine_type, machine.location,
            False, None
        )

        # Free the machine
        await self.machine_pool.free_machine(machine.machine_id)

        # Move piece to next stage
        next_stage = self._get_next_production_stage(piece.current_stage)

        logger.info(f"Piece {piece.piece_id} completed {piece.current_stage.value}, moving to: {next_stage.value}")

        if next_stage == ProductionStage.COMPLETED:
            # Piece has completed all stages
            piece.current_stage = ProductionStage.COMPLETED

            # Send piece completion message and update lot progress
            lot = self.lots.get(piece.lot_code)
            if lot:
                await self._send_piece_completion_message(piece, lot)

                # Check if entire lot is complete
                if lot.is_lot_complete():
                    # All pieces in lot are complete
                    await self._complete_lot(lot)
        else:
            # Move piece to next stage queue
            piece.current_stage = next_stage
            await self.queues[next_stage].add(piece)
            logger.info(f"Added piece {piece.piece_id} to {next_stage.value} queue")

        logger.info(f"Completed processing piece {piece.piece_id} on {machine.machine_id}")

    async def _complete_lot(self, lot: ProductionLot):
        """Complete an entire lot when all pieces are finished"""
        now = datetime.now()

        logger.info(f"Lot {lot.lot_code} completed - all {lot.quantity} pieces finished")

        # Update lot status to completed (CRITICAL FIX: Don't delete the lot)
        lot.current_stage = ProductionStage.COMPLETED

        # NOTE: No longer sending lot-level completion data here since we now send
        # piece-by-piece completion messages. The final piece completion message
        # will have lot_produced_quantity == lot_total_quantity indicating lot completion.

        # Update monitoring for completed lot
        monitor.update_lot_status(
            lot.lot_code, lot.customer, lot.quantity,
            lot.location, "completed"
        )
        monitor.complete_lot(lot.lot_code)


        # Keep the lot in self.lots but mark it as completed
        # This allows status tracking to show "completed" instead of removing it entirely
        logger.info(f"Lot {lot.lot_code} marked as completed and retained for status tracking")



    async def _send_piece_completion_message(self, piece: ProductionPiece, lot: ProductionLot):
        """Send piece completion message when a piece finishes all 4 stages"""
        try:
            # Increment the lot's completed pieces counter
            lot.pieces_produced += 1
            
            # Update monitoring with current piece completion count
            monitor.update_piece_completion(lot.lot_code, lot.pieces_produced)
            
            # Update database with current pieces produced count
            if hasattr(self, 'db'):
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.db.connection.execute(
                            "UPDATE lots SET pieces_produced = ? WHERE lot_code = ?",
                            (lot.pieces_produced, lot.lot_code)
                        )
                    )
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.db.connection.commit()
                    )
                except Exception as db_error:
                    logger.error(f"Failed to update pieces_produced for lot {lot.lot_code}: {db_error}")

            # Calculate individual piece timing for each stage
            cnc_duration = 0
            lathe_duration = 0
            assembly_duration = 0
            test_duration = 0

            if piece.cnc_start and piece.cnc_end:
                cnc_duration = max(1, int((piece.cnc_end - piece.cnc_start).total_seconds() / 60))
            if piece.lathe_start and piece.lathe_end:
                lathe_duration = max(1, int((piece.lathe_end - piece.lathe_start).total_seconds() / 60))
            if piece.assembly_start and piece.assembly_end:
                assembly_duration = max(1, int((piece.assembly_end - piece.assembly_start).total_seconds() / 60))
            if piece.test_start and piece.test_end:
                test_duration = max(1, int((piece.test_end - piece.test_start).total_seconds() / 60))

            logger.debug(f"Piece {piece.piece_id} durations - CNC: {cnc_duration}min, Lathe: {lathe_duration}min, Assembly: {assembly_duration}min, Test: {test_duration}min")

            # Get timezone-aware timestamps
            utc_now = datetime.now(timezone.utc)
            local_tz = pytz.timezone(self._get_location_timezone(piece.location))
            local_now = utc_now.astimezone(local_tz)

            # Create piece completion data (updated format)
            completion_data = {
                "lot_code": piece.lot_code,
                "lot_total_quantity": lot.quantity,
                "lot_produced_quantity": lot.pieces_produced,
                "cnc_duration": cnc_duration,
                "lathe_duration": lathe_duration,
                "assembly_duration": assembly_duration,
                "test_duration": test_duration,
                "site": piece.location,
                "local_timestamp": local_now.isoformat(),
                "utc_timestamp": utc_now.isoformat()
            }

            # Send to Kafka
            await self.kafka_sender.send_piece_completion_data(completion_data)

            logger.info(f"Piece {piece.piece_id} completed - lot progress: {lot.pieces_produced}/{lot.quantity}")
            
            # Check if lot is now complete (all pieces finished)
            if lot.pieces_produced >= lot.quantity:
                await self._complete_lot(lot)

        except Exception as e:
            logger.error(f"Failed to send piece completion message for piece {piece.piece_id}: {e}")
    
    async def _complete_lot(self, lot: ProductionLot):
        """Mark a lot as completed when all pieces are finished"""
        try:
            # Update lot stage to completed
            lot.current_stage = ProductionStage.COMPLETED
            
            # Update database - mark lot as completed
            if hasattr(self, 'db'):
                # Update lot status in database
                # We'll use a SQL update since we need to update the lot record directly
                import sqlite3
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.db.connection.execute(
                            "UPDATE lots SET current_stage = 'completed' WHERE lot_code = ?",
                            (lot.lot_code,)
                        )
                    )
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.db.connection.commit()
                    )
                except Exception as db_error:
                    logger.error(f"Failed to update lot {lot.lot_code} in database: {db_error}")
            
            # Update monitoring
            monitor.complete_lot(lot.lot_code)
            
            logger.info(f"🎉 Lot {lot.lot_code} COMPLETED! All {lot.quantity} pieces finished production.")
            
        except Exception as e:
            logger.error(f"Error completing lot {lot.lot_code}: {e}")

    def _get_location_timezone(self, location: str) -> str:
        """Get timezone string for a location"""
        timezone_map = {
            "Italy": "Europe/Rome",
            "Brazil": "America/Sao_Paulo",
            "Vietnam": "Asia/Ho_Chi_Minh"
        }
        return timezone_map.get(location, "Europe/Rome")  # Default to Italy timezone

    async def _send_piece_telemetry(self, piece: ProductionPiece, machine: Machine, status: str):
        """Send machine telemetry data for piece processing"""
        # This delegates to the existing machine telemetry system
        # We create a temporary lot-like object for compatibility
        temp_lot = type('TempLot', (), {
            'lot_code': piece.lot_code,
            'customer': piece.customer,
            'quantity': 1,  # Single piece
            'location': piece.location
        })()

        await self._send_machine_telemetry(temp_lot, machine, status)

    def _get_pieces_per_cycle(self, machine_type: str) -> int:
        """Get how many pieces a machine type produces per processing cycle"""
        # Different machine types produce different amounts per cycle
        pieces_per_cycle = {
            "cnc": random.randint(1, 5),    # CNC produces 1-5 pieces per cycle
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


            # Send telemetry data
            telemetry_data = simulator.generate_measurement_data()
            await self.kafka_sender.send_telemetry_data(telemetry_data, machine.machine_type)

    # NOTE: _send_end_of_cycle_data method removed - replaced with piece-by-piece completion messaging
    
    
    def _get_next_stage(self, current_stage: ProductionStage) -> ProductionStage:
        """Get the next processing stage (for starting)"""
        transitions = {
            ProductionStage.QUEUED: ProductionStage.CNC,
            ProductionStage.CNC: ProductionStage.LATHE,
            ProductionStage.LATHE: ProductionStage.ASSEMBLY,
            ProductionStage.ASSEMBLY: ProductionStage.TEST
        }
        return transitions.get(current_stage, current_stage)
    
    def _get_processing_stage(self, queue_stage: ProductionStage) -> ProductionStage:
        """Get the processing stage for a given queue stage"""
        transitions = {
            ProductionStage.QUEUED: ProductionStage.CNC,
            ProductionStage.CNC: ProductionStage.CNC,
            ProductionStage.LATHE: ProductionStage.LATHE,
            ProductionStage.ASSEMBLY: ProductionStage.ASSEMBLY,
            ProductionStage.TEST: ProductionStage.TEST
        }
        return transitions.get(queue_stage, queue_stage)
    
    def _get_next_production_stage(self, current_stage: ProductionStage) -> ProductionStage:
        """Get the next queue stage (after completion)"""
        transitions = {
            ProductionStage.CNC: ProductionStage.LATHE,
            ProductionStage.LATHE: ProductionStage.ASSEMBLY,
            ProductionStage.ASSEMBLY: ProductionStage.TEST,
            ProductionStage.TEST: ProductionStage.COMPLETED
        }
        return transitions.get(current_stage, ProductionStage.COMPLETED)
    
    async def _restore_lots_from_database(self):
        """Restore incomplete lots from database when simulator starts"""
        try:
            # Get all active lots from database
            active_lots = await self.db.get_all_active_lots()
            
            for lot_data in active_lots:
                lot_code = lot_data['lot_code']
                logger.info(f"Restoring lot {lot_code} from database...")
                
                # Create ProductionLot object
                lot = ProductionLot(
                    lot_code=lot_code,
                    customer=lot_data['customer'],
                    quantity=lot_data['quantity'],
                    location=lot_data['location'],
                    priority=lot_data.get('priority', 'normal'),
                    current_stage=ProductionStage(lot_data['current_stage'])
                )
                
                # Set timing data if available
                if lot_data.get('created_at'):
                    lot.created_at = datetime.fromisoformat(lot_data['created_at'].replace('Z', '+00:00'))
                
                # Get all pieces for this lot from database (all stages)
                all_pieces = []
                for stage in ['queued', 'cnc', 'lathe', 'assembly', 'test']:
                    stage_pieces = await self.db.get_queued_pieces(stage, lot_data['location'])
                    lot_pieces_in_stage = [p for p in stage_pieces if p['lot_code'] == lot_code]
                    all_pieces.extend(lot_pieces_in_stage)
                
                # Create ProductionPiece objects and add to lot
                for piece_data in all_pieces:
                    piece = ProductionPiece(
                        piece_id=piece_data['piece_id'],
                        lot_code=lot_code,
                        piece_number=piece_data['piece_number'],
                        customer=lot_data['customer'],
                        location=lot_data['location'],
                        priority=lot_data.get('priority', 'normal'),
                        current_stage=ProductionStage(piece_data['current_stage'])
                    )
                    
                    # Add piece to lot tracking
                    lot.pieces_in_production[piece.piece_id] = piece
                    
                    # Add piece to appropriate queue
                    stage = ProductionStage(piece_data['current_stage'])
                    await self.queues[stage].add(piece)
                
                # Add lot to in-memory tracking
                self.lots[lot_code] = lot
                
                # Update monitoring
                monitor.update_lot_status(
                    lot.lot_code, lot.customer, lot.quantity,
                    lot.location, lot.current_stage.value, lot.created_at
                )
                
                # Update piece completion count
                completed_pieces = lot_data.get('completed_pieces', 0)
                if completed_pieces > 0:
                    lot.pieces_produced = completed_pieces
                    monitor.update_piece_completion(lot_code, completed_pieces)
                
                logger.info(f"Restored lot {lot_code}: {len(all_pieces)} pieces across production stages")
            
            if active_lots:
                logger.info(f"Successfully restored {len(active_lots)} lots from database")
            else:
                logger.info("No incomplete lots found in database to restore")
                
        except Exception as e:
            logger.error(f"Error restoring lots from database: {e}")
    
    async def start(self):
        """Start the production coordinator with concurrent location processing"""
        # Initialize database first
        await self.db.initialize()
        
        # Restore incomplete lots from database
        await self._restore_lots_from_database()
        
        self.running = True
        monitor.start()
        logger.info("Production coordinator started with concurrent location processing")

        # Start concurrent tasks for each location plus shared tasks
        await asyncio.gather(
            # Concurrent location processors
            self.process_queues_for_location("Italy"),
            self.process_queues_for_location("Brazil"),
            self.process_queues_for_location("Vietnam"),
            # Shared tasks
            self._high_frequency_telemetry_loop(),
            self._random_maintenance_events()
        )
    
    async def _high_frequency_telemetry_loop(self):
        """Send telemetry data every 5 seconds for active machines"""
        while self.running:
            try:
                if self.telemetry_enabled:
                    # Send telemetry for all busy machines
                    logger.info(f"Telemetry loop: sending data every {self.telemetry_interval} seconds")
                    for machine in self.machine_pool.all_machines.values():
                        if machine.is_busy and machine.current_lot:
                            # Find the lot being processed
                            lot = self.lots.get(machine.current_lot)
                            if lot:
                                logger.info(f"Sending telemetry for machine {machine.machine_id}")
                                await self._send_machine_telemetry(lot, machine, "processing")

                # Wait for next telemetry interval
                await asyncio.sleep(self.telemetry_interval)

            except Exception as e:
                logger.error(f"Error in high-frequency telemetry loop: {e}")
                await asyncio.sleep(self.telemetry_interval)  # Continue after error with proper interval

    async def stop(self):
        """Stop the production coordinator"""
        self.running = False
        await monitor.stop()
        await self.db.close()
        logger.info("Production coordinator stopped")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current production status"""
        # Calculate total pieces in production
        total_pieces = sum(len(lot.pieces_in_production) for lot in self.lots.values())

        status = {
            "active_lots": len(self.lots),
            "total_pieces_in_production": total_pieces,
            "queues": {},
            "machines": self.machine_pool.get_machine_status()
        }

        for stage, queue in self.queues.items():
            lot_codes_in_queue = await queue.get_lots_in_queue()
            queue_size = await queue.size()
            status["queues"][stage.value] = {
                "pieces": queue_size,
                "lots_represented": len(lot_codes_in_queue),
                "lot_codes": list(lot_codes_in_queue)
            }

        return status

    async def delete_queued_lots(self) -> Dict[str, Any]:
        """Delete all queued lots and their pieces from the QUEUED stage"""
        try:
            # Clear the QUEUED stage queue
            cleared_pieces = await self.queues[ProductionStage.QUEUED].clear_all()

            # Find lots that are only in QUEUED stage (not yet started processing)
            lots_to_remove = []
            for lot_code, lot in self.lots.items():
                if lot.current_stage == ProductionStage.QUEUED:
                    # Check if any pieces are in other stages
                    pieces_in_other_stages = False
                    for stage in [ProductionStage.CNC, ProductionStage.LATHE, ProductionStage.ASSEMBLY, ProductionStage.TEST]:
                        stage_pieces = await self.queues[stage].get_pieces()
                        if any(piece.lot_code == lot_code for piece in stage_pieces):
                            pieces_in_other_stages = True
                            break

                    # Also check if any machines are processing pieces from this lot
                    lot_being_processed = any(
                        machine.current_lot == lot_code and machine.is_busy
                        for machine in self.machine_pool.all_machines.values()
                    )

                    if not pieces_in_other_stages and not lot_being_processed:
                        lots_to_remove.append(lot_code)

            # Remove lots that are completely queued
            removed_lots = []
            for lot_code in lots_to_remove:
                lot = self.lots.pop(lot_code, None)
                if lot:
                    removed_lots.append({
                        "lot_code": lot_code,
                        "customer": lot.customer,
                        "quantity": lot.quantity,
                        "location": lot.location
                    })

                    # Update monitoring
                    monitor.complete_lot(lot_code)

            # Update queue monitoring
            queue_size = await self.queues[ProductionStage.QUEUED].size()
            monitor.update_queue_status("queued", queue_size)


            logger.info(f"Deleted {len(removed_lots)} queued lots and cleared {cleared_pieces} pieces from queue")

            return {
                "success": True,
                "deleted_lots": removed_lots,
                "total_deleted": len(removed_lots),
                "pieces_cleared": cleared_pieces
            }

        except Exception as e:
            logger.error(f"Error deleting queued lots: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_specific_lot(self, lot_code: str) -> Dict[str, Any]:
        """Delete a specific lot and all its pieces"""
        try:
            if lot_code not in self.lots:
                return {
                    "success": False,
                    "error": f"Lot {lot_code} not found",
                    "lot_code": lot_code
                }
            
            lot = self.lots[lot_code]
            pieces_cleared = 0
            
            # Remove pieces from all queues
            for stage, queue in self.queues.items():
                stage_pieces = await queue.get_pieces()
                lot_pieces_in_stage = [piece for piece in stage_pieces if piece.lot_code == lot_code]
                
                for piece in lot_pieces_in_stage:
                    removed_piece = await queue.remove_specific_piece(piece.piece_id)
                    if removed_piece:
                        pieces_cleared += 1
            
            # Free any machines currently processing this lot
            for machine in self.machine_pool.all_machines.values():
                if machine.current_lot == lot_code and machine.is_busy:
                    await self.machine_pool.free_machine(machine.machine_id)
                    logger.info(f"Freed machine {machine.machine_id} from deleted lot {lot_code}")
            
            # Remove from database
            if hasattr(self, 'db'):
                await self.db.delete_lot(lot_code)
            
            # Remove from in-memory tracking
            del self.lots[lot_code]
            
            # Remove from monitoring
            monitor.delete_lot(lot_code)
            
            logger.info(f"Successfully deleted lot {lot_code} with {pieces_cleared} pieces")
            
            return {
                "success": True,
                "message": f"Successfully deleted lot {lot_code}",
                "lot_code": lot_code,
                "pieces_cleared": pieces_cleared
            }
            
        except Exception as e:
            logger.error(f"Error deleting lot {lot_code}: {e}")
            return {
                "success": False,
                "error": str(e),
                "lot_code": lot_code
            }

    async def set_machine_maintenance(self, machine_id: str, in_maintenance: bool, reason: str = None) -> bool:
        """Set machine maintenance status"""
        await self.machine_pool.set_machine_maintenance(machine_id, in_maintenance, reason)
        return True

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
                        

            except Exception as e:
                logger.error(f"Error in random maintenance events: {e}")
                await asyncio.sleep(60)