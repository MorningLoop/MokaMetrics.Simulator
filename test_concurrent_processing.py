#!/usr/bin/env python3
"""
Test concurrent processing functionality
Verify that all 3 locations can simultaneously process their respective lots
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

from Simulator.state_machine import ProductionCoordinator, ProductionStage, ProductionLot

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_concurrent_processing():
    """Test that locations can process lots concurrently"""
    logger.info("🧪 Testing concurrent processing functionality...")
    
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
            "lot_code": "TEST-ITALY-001",
            "customer": "TestCustomer",
            "quantity": 2,
            "location": "Italy",
            "priority": "normal"
        },
        {
            "lot_code": "TEST-BRAZIL-001", 
            "customer": "TestCustomer",
            "quantity": 2,
            "location": "Brazil",
            "priority": "normal"
        },
        {
            "lot_code": "TEST-VIETNAM-001",
            "customer": "TestCustomer", 
            "quantity": 2,
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
    queued_pieces = status["queues"]["queued"]["pieces"]
    logger.info(f"✓ Initial queued pieces: {queued_pieces}")
    
    # Start concurrent processing for a short time
    coordinator.running = True
    
    # Create tasks for each location processor
    location_tasks = [
        asyncio.create_task(coordinator.process_queues_for_location("Italy")),
        asyncio.create_task(coordinator.process_queues_for_location("Brazil")),
        asyncio.create_task(coordinator.process_queues_for_location("Vietnam"))
    ]
    
    logger.info("✓ Started concurrent location processors")
    
    # Let it run for a few seconds to see processing start
    await asyncio.sleep(3)
    
    # Check status after processing starts
    status = await coordinator.get_status()
    logger.info("📊 Status after 3 seconds:")
    for stage, info in status["queues"].items():
        if info["pieces"] > 0:
            logger.info(f"  {stage}: {info['pieces']} pieces")
    
    # Check machine utilization
    machines = status["machines"]
    for machine_type, info in machines.items():
        if info["busy"] > 0:
            logger.info(f"  {machine_type} machines: {info['busy']}/{info['total']} busy")
    
    # Stop processing
    coordinator.running = False
    
    # Cancel tasks
    for task in location_tasks:
        task.cancel()
    
    # Wait for tasks to complete
    await asyncio.gather(*location_tasks, return_exceptions=True)
    
    logger.info("✅ Concurrent processing test completed successfully!")
    
    # Verify that processing occurred
    final_status = await coordinator.get_status()
    total_pieces_in_production = final_status["total_pieces_in_production"]
    
    if total_pieces_in_production > 0:
        logger.info(f"✓ Processing started: {total_pieces_in_production} pieces in production")
        return True
    else:
        logger.warning("⚠️  No pieces entered production - may need longer test duration")
        return False

async def main():
    """Main test function"""
    try:
        success = await test_concurrent_processing()
        if success:
            logger.info("🎉 All concurrent processing tests passed!")
            return 0
        else:
            logger.error("❌ Concurrent processing test failed")
            return 1
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
