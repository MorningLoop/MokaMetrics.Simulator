#!/usr/bin/env python3
"""
Test the delete queued lots functionality
"""

import asyncio
import logging
import sys
import os
import yaml
from datetime import datetime

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from Simulator.state_machine import ProductionCoordinator, ProductionStage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockKafkaSender:
    """Mock Kafka sender for testing"""
    def __init__(self):
        self.kafka_producer = self
    
    async def send_and_wait(self, topic, key, value):
        """Mock send method"""
        pass
    
    async def send_to_kafka(self, topic, data):
        """Mock send_to_kafka method"""
        pass

async def test_delete_queued_lots():
    """Test the delete queued lots functionality"""
    logger.info("🧪 Testing delete queued lots functionality...")
    
    # Create production coordinator with mock kafka sender
    mock_kafka = MockKafkaSender()
    coordinator = ProductionCoordinator(mock_kafka)
    
    # Load config and initialize machines
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    await coordinator.initialize_machines(config['machines'])
    logger.info("✓ Machines initialized")
    
    # Create test lots for each location
    test_lots = [
        {
            "lot_code": "DELETE-TEST-ITALY-001",
            "customer": "TestCustomer",
            "quantity": 3,
            "location": "Italy",
            "priority": "normal"
        },
        {
            "lot_code": "DELETE-TEST-BRAZIL-001", 
            "customer": "TestCustomer",
            "quantity": 2,
            "location": "Brazil",
            "priority": "high"
        },
        {
            "lot_code": "DELETE-TEST-VIETNAM-001",
            "customer": "TestCustomer", 
            "quantity": 4,
            "location": "Vietnam",
            "priority": "normal"
        }
    ]
    
    # Add lots to coordinator
    for lot_data in test_lots:
        await coordinator.add_lot(lot_data)
    
    logger.info("✓ Added test lots for all 3 locations")
    
    # Check initial queue status
    status = await coordinator.get_status()
    initial_queued_pieces = status["queues"]["queued"]["pieces"]
    initial_active_lots = status["active_lots"]
    
    logger.info(f"✓ Initial state: {initial_queued_pieces} queued pieces, {initial_active_lots} active lots")
    
    # Test the delete functionality
    result = await coordinator.delete_queued_lots()
    
    if result["success"]:
        deleted_count = result["total_deleted"]
        pieces_cleared = result["pieces_cleared"]
        logger.info(f"✅ Delete operation successful:")
        logger.info(f"   - Deleted lots: {deleted_count}")
        logger.info(f"   - Cleared pieces: {pieces_cleared}")
        
        # Verify the results
        final_status = await coordinator.get_status()
        final_queued_pieces = final_status["queues"]["queued"]["pieces"]
        final_active_lots = final_status["active_lots"]
        
        logger.info(f"✓ Final state: {final_queued_pieces} queued pieces, {final_active_lots} active lots")
        
        # Verify that queued pieces were cleared
        if final_queued_pieces == 0:
            logger.info("✅ All queued pieces successfully cleared")
        else:
            logger.warning(f"⚠️  Still {final_queued_pieces} pieces in queue")
        
        # Verify that lots were removed
        if final_active_lots == 0:
            logger.info("✅ All lots successfully removed")
        else:
            logger.warning(f"⚠️  Still {final_active_lots} active lots")
        
        return True
    else:
        logger.error(f"❌ Delete operation failed: {result.get('error', 'Unknown error')}")
        return False

async def test_delete_empty_queue():
    """Test deleting when queue is already empty"""
    logger.info("🧪 Testing delete on empty queue...")
    
    # Create fresh coordinator
    mock_kafka = MockKafkaSender()
    coordinator = ProductionCoordinator(mock_kafka)
    
    # Load config and initialize machines
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    await coordinator.initialize_machines(config['machines'])
    
    # Test delete on empty queue
    result = await coordinator.delete_queued_lots()
    
    if result["success"] and result["total_deleted"] == 0:
        logger.info("✅ Empty queue delete test passed")
        return True
    else:
        logger.error("❌ Empty queue delete test failed")
        return False

async def main():
    """Main test function"""
    try:
        logger.info("🚀 Starting delete queued lots tests...")
        logger.info("=" * 50)
        
        # Test 1: Delete with lots in queue
        success1 = await test_delete_queued_lots()
        logger.info("")
        
        # Test 2: Delete empty queue
        success2 = await test_delete_empty_queue()
        logger.info("")
        
        if success1 and success2:
            logger.info("🎉 All delete queued lots tests passed!")
            return 0
        else:
            logger.error("❌ Some tests failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
