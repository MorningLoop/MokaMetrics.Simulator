"""
Real-time monitoring system for MokaMetrics Simulator
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import json

@dataclass
class MessageStats:
    """Statistics for message sending"""
    total_sent: int = 0
    sent_last_minute: int = 0
    sent_last_second: int = 0
    last_sent_time: Optional[datetime] = None
    recent_timestamps: deque = field(default_factory=lambda: deque(maxlen=60))  # Last 60 seconds

@dataclass
class MachineStats:
    """Statistics for machine utilization"""
    machine_id: str
    machine_type: str
    location: str
    is_busy: bool = False
    current_lot: Optional[str] = None
    total_processing_time: float = 0.0  # Total time spent processing (minutes)
    lots_processed: int = 0
    utilization_percentage: float = 0.0
    busy_since: Optional[datetime] = None

@dataclass
class LotStats:
    """Statistics for lot processing"""
    lot_code: str
    customer: str
    quantity: int
    location: str
    current_stage: str
    created_at: datetime
    stage_start_time: Optional[datetime] = None
    total_processing_time: float = 0.0  # Minutes
    stages_completed: List[str] = field(default_factory=list)
    completed_pieces: int = 0  # Track how many pieces have completed all stages

@dataclass
class QueueStats:
    """Statistics for production queues"""
    stage: str
    queue_length: int = 0
    high_priority_length: int = 0
    average_wait_time: float = 0.0  # Minutes
    total_processed: int = 0

class SimulatorMonitor:
    """Real-time monitoring system for the simulator"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.message_stats: Dict[str, MessageStats] = defaultdict(MessageStats)
        self.machine_stats: Dict[str, MachineStats] = {}
        self.lot_stats: Dict[str, LotStats] = {}
        self.queue_stats: Dict[str, QueueStats] = {}
        
        # Performance metrics
        self.total_lots_completed = 0
        self.total_messages_sent = 0
        self.average_cycle_time = 0.0
        
        # Thread-safe lock for updating stats
        self._lock = threading.Lock()
        
        # Start background cleanup task
        self._cleanup_task = None
        self._running = False
    
    def start(self):
        """Start the monitoring system"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_old_data())
    
    async def stop(self):
        """Stop the monitoring system"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    def record_message_sent(self, topic: str, key: str = None):
        """Record that a message was sent to a topic"""
        with self._lock:
            now = datetime.now()
            stats = self.message_stats[topic]
            stats.total_sent += 1
            stats.last_sent_time = now
            stats.recent_timestamps.append(now)
            self.total_messages_sent += 1
    
    def update_machine_status(self, machine_id: str, machine_type: str, location: str, 
                            is_busy: bool, current_lot: str = None):
        """Update machine status"""
        with self._lock:
            if machine_id not in self.machine_stats:
                self.machine_stats[machine_id] = MachineStats(
                    machine_id=machine_id,
                    machine_type=machine_type,
                    location=location
                )
            
            machine = self.machine_stats[machine_id]
            
            # If machine is becoming busy
            if is_busy and not machine.is_busy:
                machine.busy_since = datetime.now()
            
            # If machine is becoming free
            elif not is_busy and machine.is_busy:
                if machine.busy_since:
                    processing_time = (datetime.now() - machine.busy_since).total_seconds() / 60
                    machine.total_processing_time += processing_time
                    machine.lots_processed += 1
                machine.busy_since = None
            
            machine.is_busy = is_busy
            machine.current_lot = current_lot
            
            # Calculate utilization
            uptime = (datetime.now() - self.start_time).total_seconds() / 60
            if uptime > 0:
                machine.utilization_percentage = (machine.total_processing_time / uptime) * 100
    
    def update_lot_status(self, lot_code: str, customer: str, quantity: int, location: str,
                         current_stage: str, created_at: datetime = None):
        """Update lot status"""
        with self._lock:
            if lot_code not in self.lot_stats:
                self.lot_stats[lot_code] = LotStats(
                    lot_code=lot_code,
                    customer=customer,
                    quantity=quantity,
                    location=location,
                    current_stage=current_stage,
                    created_at=created_at or datetime.now()
                )
            else:
                lot = self.lot_stats[lot_code]
                if lot.current_stage != current_stage:
                    # Stage changed, record completion
                    if lot.current_stage not in lot.stages_completed:
                        lot.stages_completed.append(lot.current_stage)
                    lot.stage_start_time = datetime.now()
                lot.current_stage = current_stage
    
    def update_piece_completion(self, lot_code: str, completed_pieces: int):
        """Update the number of completed pieces for a lot"""
        with self._lock:
            if lot_code in self.lot_stats:
                self.lot_stats[lot_code].completed_pieces = completed_pieces
    
    def complete_lot(self, lot_code: str):
        """Mark a lot as completed"""
        with self._lock:
            if lot_code in self.lot_stats:
                lot = self.lot_stats[lot_code]
                lot.total_processing_time = (datetime.now() - lot.created_at).total_seconds() / 60
                lot.completed_pieces = lot.quantity  # All pieces completed
                self.total_lots_completed += 1
                
                # Update average cycle time
                if self.total_lots_completed > 0:
                    total_time = sum(lot.total_processing_time for lot in self.lot_stats.values() 
                                   if lot.current_stage == "completed")
                    self.average_cycle_time = total_time / self.total_lots_completed
    
    def delete_lot(self, lot_code: str):
        """Remove a lot from monitoring completely"""
        with self._lock:
            if lot_code in self.lot_stats:
                del self.lot_stats[lot_code]
    
    def update_queue_status(self, stage: str, queue_length: int, high_priority_length: int = 0):
        """Update queue status"""
        with self._lock:
            if stage not in self.queue_stats:
                self.queue_stats[stage] = QueueStats(stage=stage)
            
            queue = self.queue_stats[stage]
            queue.queue_length = queue_length
            queue.high_priority_length = high_priority_length
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        with self._lock:
            now = datetime.now()
            
            # Calculate messages per second/minute for each topic
            topic_stats = {}
            for topic, stats in self.message_stats.items():
                # Count messages in last second and minute
                one_second_ago = now - timedelta(seconds=1)
                one_minute_ago = now - timedelta(minutes=1)
                
                recent_second = sum(1 for ts in stats.recent_timestamps if ts >= one_second_ago)
                recent_minute = sum(1 for ts in stats.recent_timestamps if ts >= one_minute_ago)
                
                topic_stats[topic] = {
                    "total_sent": stats.total_sent,
                    "per_second": recent_second,
                    "per_minute": recent_minute,
                    "last_sent": stats.last_sent_time.isoformat() if stats.last_sent_time else None
                }
            
            # Get active lots with progress
            active_lots = []
            for lot in self.lot_stats.values():
                if lot.current_stage != "completed":
                    # Calculate progress based on completed pieces vs total quantity
                    completed_pieces = getattr(lot, 'completed_pieces', 0)
                    progress_percentage = round((completed_pieces / lot.quantity) * 100, 1) if lot.quantity > 0 else 0
                    
                    active_lots.append({
                        "lot_code": lot.lot_code,
                        "customer": lot.customer,
                        "quantity": lot.quantity,
                        "location": lot.location,
                        "current_stage": lot.current_stage,
                        "processing_time_minutes": round(lot.total_processing_time, 2),
                        "completed_pieces": completed_pieces,
                        "progress_percentage": progress_percentage
                    })
            
            # Get machine utilization
            machine_utilization = [
                {
                    "machine_id": machine.machine_id,
                    "machine_type": machine.machine_type,
                    "location": machine.location,
                    "is_busy": machine.is_busy,
                    "current_lot": machine.current_lot,
                    "utilization_percentage": round(machine.utilization_percentage, 2),
                    "lots_processed": machine.lots_processed,
                    "total_processing_time_minutes": round(machine.total_processing_time, 2)
                }
                for machine in self.machine_stats.values()
            ]
            
            # Get queue status
            queue_status = [
                {
                    "stage": queue.stage,
                    "queue_length": queue.queue_length,
                    "high_priority_length": queue.high_priority_length,
                    "total_processed": queue.total_processed
                }
                for queue in self.queue_stats.values()
            ]
            
            uptime_seconds = (now - self.start_time).total_seconds()
            
            return {
                "timestamp": now.isoformat(),
                "uptime_seconds": round(uptime_seconds, 2),
                "uptime_formatted": str(timedelta(seconds=int(uptime_seconds))),
                "total_lots_completed": self.total_lots_completed,
                "total_messages_sent": self.total_messages_sent,
                "average_cycle_time_minutes": round(self.average_cycle_time, 2),
                "messages_per_second": sum(stats["per_second"] for stats in topic_stats.values()),
                "messages_per_minute": sum(stats["per_minute"] for stats in topic_stats.values()),
                "topic_stats": topic_stats,
                "active_lots": active_lots,
                "machine_utilization": machine_utilization,
                "queue_status": queue_status
            }
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data periodically"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Clean up every minute
                
                with self._lock:
                    now = datetime.now()
                    cutoff = now - timedelta(minutes=5)  # Keep last 5 minutes
                    
                    # Clean up old timestamps in message stats
                    for stats in self.message_stats.values():
                        while stats.recent_timestamps and stats.recent_timestamps[0] < cutoff:
                            stats.recent_timestamps.popleft()
                    
                    # Remove completed lots older than 10 minutes
                    old_cutoff = now - timedelta(minutes=10)
                    completed_lots = [
                        lot_code for lot_code, lot in self.lot_stats.items()
                        if lot.current_stage == "completed" and lot.created_at < old_cutoff
                    ]
                    for lot_code in completed_lots:
                        del self.lot_stats[lot_code]
                        
            except Exception as e:
                print(f"Error in monitoring cleanup: {e}")

# Global monitor instance
monitor = SimulatorMonitor()
