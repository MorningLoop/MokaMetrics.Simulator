"""
SQLite database module for persistent lot and piece tracking
"""

import sqlite3
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

logger = logging.getLogger(__name__)

class ProductionDatabase:
    """SQLite database for persistent production tracking"""
    
    def __init__(self, db_path: str = "/app/data/production.db"):
        self.db_path = db_path
        self.connection = None
        
    async def initialize(self):
        """Initialize database connection and create tables"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Create tables
        await asyncio.get_event_loop().run_in_executor(None, self._create_tables)
        logger.info(f"Database initialized at {self.db_path}")
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.connection.cursor()
        
        # Lots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lots (
                lot_code TEXT PRIMARY KEY,
                customer TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                location TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                current_stage TEXT DEFAULT 'queued',
                current_machine TEXT,
                pieces_produced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stage_start_time TIMESTAMP,
                cnc_start TIMESTAMP,
                cnc_end TIMESTAMP,
                lathe_start TIMESTAMP,
                lathe_end TIMESTAMP,
                assembly_start TIMESTAMP,
                assembly_end TIMESTAMP,
                test_start TIMESTAMP,
                test_end TIMESTAMP,
                completed_at TIMESTAMP,
                machine_times TEXT  -- JSON string of machine_id -> time_minutes
            )
        """)
        
        # Pieces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pieces (
                piece_id TEXT PRIMARY KEY,
                lot_code TEXT NOT NULL,
                piece_number INTEGER NOT NULL,
                customer TEXT NOT NULL,
                location TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                current_stage TEXT DEFAULT 'queued',
                current_machine TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stage_start_time TIMESTAMP,
                cnc_start TIMESTAMP,
                cnc_end TIMESTAMP,
                lathe_start TIMESTAMP,
                lathe_end TIMESTAMP,
                assembly_start TIMESTAMP,
                assembly_end TIMESTAMP,
                test_start TIMESTAMP,
                test_end TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (lot_code) REFERENCES lots (lot_code) ON DELETE CASCADE
            )
        """)
        
        # Processing queues table (for queue management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_queues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                piece_id TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (piece_id) REFERENCES pieces (piece_id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_location ON lots (location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_stage ON lots (current_stage)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pieces_lot ON pieces (lot_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pieces_stage ON pieces (current_stage)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_stage ON processing_queues (stage)")
        
        self.connection.commit()
        logger.info("Database tables created successfully")
    
    async def add_lot(self, lot_data: Dict[str, Any]) -> bool:
        """Add a new lot to the database"""
        try:
            # Support both old and new field names
            lot_code = lot_data.get("lot_code") or lot_data.get("codice_lotto")
            customer = lot_data.get("customer") or lot_data.get("cliente")  
            quantity = lot_data.get("quantity") or lot_data.get("quantita")
            priority = lot_data.get("priority") or lot_data.get("priorita", "normal")
            location = lot_data["location"]
            
            cursor = self.connection.cursor()
            
            # Insert lot
            cursor.execute("""
                INSERT OR REPLACE INTO lots 
                (lot_code, customer, quantity, location, priority, current_stage, created_at)
                VALUES (?, ?, ?, ?, ?, 'queued', CURRENT_TIMESTAMP)
            """, (lot_code, customer, quantity, location, priority))
            
            # Create and insert pieces
            for piece_num in range(1, quantity + 1):
                piece_id = f"{lot_code}_P{piece_num:03d}"
                cursor.execute("""
                    INSERT OR REPLACE INTO pieces 
                    (piece_id, lot_code, piece_number, customer, location, priority, current_stage, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'queued', CURRENT_TIMESTAMP)
                """, (piece_id, lot_code, piece_num, customer, location, priority))
                
                # Add piece to queued stage
                cursor.execute("""
                    INSERT INTO processing_queues (stage, piece_id, priority)
                    VALUES ('queued', ?, ?)
                """, (piece_id, priority))
            
            self.connection.commit()
            logger.info(f"Added lot {lot_code} with {quantity} pieces to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add lot to database: {e}")
            self.connection.rollback()
            return False
    
    async def get_lots_by_location(self, location: str) -> List[Dict[str, Any]]:
        """Get all lots for a specific location"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM lots 
            WHERE location = ? AND current_stage != 'completed'
            ORDER BY created_at
        """, (location,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_queued_pieces(self, stage: str, location: str = None) -> List[Dict[str, Any]]:
        """Get pieces in a specific queue stage"""
        cursor = self.connection.cursor()
        
        if location:
            cursor.execute("""
                SELECT p.*, pq.queued_at
                FROM pieces p
                JOIN processing_queues pq ON p.piece_id = pq.piece_id
                WHERE pq.stage = ? AND p.location = ?
                ORDER BY p.priority DESC, pq.queued_at ASC
            """, (stage, location))
        else:
            cursor.execute("""
                SELECT p.*, pq.queued_at
                FROM pieces p
                JOIN processing_queues pq ON p.piece_id = pq.piece_id
                WHERE pq.stage = ?
                ORDER BY p.priority DESC, pq.queued_at ASC
            """, (stage,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def move_piece_to_stage(self, piece_id: str, from_stage: str, to_stage: str, machine_id: str = None) -> bool:
        """Move a piece from one stage to another"""
        try:
            cursor = self.connection.cursor()
            
            # Remove from current queue
            cursor.execute("""
                DELETE FROM processing_queues 
                WHERE piece_id = ? AND stage = ?
            """, (piece_id, from_stage))
            
            # Update piece stage
            update_fields = ["current_stage = ?"]
            params = [to_stage]
            
            if machine_id:
                update_fields.append("current_machine = ?")
                params.append(machine_id)
            else:
                update_fields.append("current_machine = NULL")
            
            # Set stage start time
            update_fields.append("stage_start_time = CURRENT_TIMESTAMP")
            
            # Set stage-specific timestamps
            stage_field_map = {
                "cnc": "cnc_start",
                "lathe": "lathe_start", 
                "assembly": "assembly_start",
                "test": "test_start"
            }
            
            if to_stage in stage_field_map:
                update_fields.append(f"{stage_field_map[to_stage]} = CURRENT_TIMESTAMP")
            elif to_stage == "completed":
                update_fields.append("completed_at = CURRENT_TIMESTAMP")
            
            params.append(piece_id)
            
            cursor.execute(f"""
                UPDATE pieces 
                SET {', '.join(update_fields)}
                WHERE piece_id = ?
            """, params)
            
            # Add to new queue if not completed
            if to_stage != "completed":
                piece_info = cursor.execute("""
                    SELECT priority FROM pieces WHERE piece_id = ?
                """, (piece_id,)).fetchone()
                
                if piece_info:
                    cursor.execute("""
                        INSERT INTO processing_queues (stage, piece_id, priority)
                        VALUES (?, ?, ?)
                    """, (to_stage, piece_id, piece_info['priority']))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to move piece {piece_id} from {from_stage} to {to_stage}: {e}")
            self.connection.rollback()
            return False
    
    async def get_lot_status(self, lot_code: str) -> Optional[Dict[str, Any]]:
        """Get current status of a lot"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM lots WHERE lot_code = ?", (lot_code,))
        lot_row = cursor.fetchone()
        
        if not lot_row:
            return None
        
        lot = dict(lot_row)
        
        # Get piece counts by stage
        cursor.execute("""
            SELECT current_stage, COUNT(*) as count
            FROM pieces 
            WHERE lot_code = ?
            GROUP BY current_stage
        """, (lot_code,))
        
        stage_counts = {row['current_stage']: row['count'] for row in cursor.fetchall()}
        lot['stage_counts'] = stage_counts
        
        return lot
    
    async def get_all_active_lots(self) -> List[Dict[str, Any]]:
        """Get all active lots with their status"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM lots 
            WHERE current_stage != 'completed'
            ORDER BY created_at
        """)
        
        lots = []
        for row in cursor.fetchall():
            lot = dict(row)
            # Add stage counts
            cursor.execute("""
                SELECT current_stage, COUNT(*) as count
                FROM pieces 
                WHERE lot_code = ?
                GROUP BY current_stage
            """, (lot['lot_code'],))
            
            stage_counts = {row['current_stage']: row['count'] for row in cursor.fetchall()}
            lot['stage_counts'] = stage_counts
            lots.append(lot)
        
        return lots
    
    async def delete_lot(self, lot_code: str) -> bool:
        """Delete a lot and all its pieces"""
        try:
            cursor = self.connection.cursor()
            
            # Delete from queues first (foreign key constraint)
            cursor.execute("""
                DELETE FROM processing_queues 
                WHERE piece_id IN (SELECT piece_id FROM pieces WHERE lot_code = ?)
            """, (lot_code,))
            
            # Delete pieces
            cursor.execute("DELETE FROM pieces WHERE lot_code = ?", (lot_code,))
            
            # Delete lot
            cursor.execute("DELETE FROM lots WHERE lot_code = ?", (lot_code,))
            
            self.connection.commit()
            logger.info(f"Deleted lot {lot_code} from database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete lot {lot_code}: {e}")
            self.connection.rollback()
            return False
    
    async def get_queue_stats(self) -> List[Dict[str, Any]]:
        """Get statistics about processing queues"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                stage,
                COUNT(*) as queue_length,
                COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_priority_length
            FROM processing_queues
            GROUP BY stage
            ORDER BY 
                CASE stage
                    WHEN 'queued' THEN 1
                    WHEN 'cnc' THEN 2
                    WHEN 'lathe' THEN 3
                    WHEN 'assembly' THEN 4
                    WHEN 'test' THEN 5
                    ELSE 6
                END
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")