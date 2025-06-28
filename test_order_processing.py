#!/usr/bin/env python3
"""
Test script for the new order processing functionality
Sends a test order message to the 'mokametrics.order' topic to verify lot creation
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiokafka import AIOKafkaProducer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderTestSender:
    """Test sender for order messages"""
    
    def __init__(self):
        self.kafka_broker = "165.227.168.240:29093"
        self.producer = None
    
    async def start(self):
        """Start the Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k is not None else None
            )
            await self.producer.start()
            logger.info(f"Kafka producer started. Connected to {self.kafka_broker}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def stop(self):
        """Stop the Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    def create_test_order(self) -> dict:
        """Create a test order with the new format"""
        today = datetime.now().strftime("%Y-%m-%d")
        deadline = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

        order = {
            "Customer": "Monster Caffeine LLC",
            "QuantityMachines": 15,
            "OrderDate": today,
            "Deadline": deadline,
            "Lots": [
                {
                    "LotCode": "ACode",
                    "TotalQuantity": 5,
                    "StartDate": today,
                    "IndustrialFacility": "Italy"
                },
                {
                    "LotCode": "AnotherCode",
                    "TotalQuantity": 5,
                    "StartDate": today,
                    "IndustrialFacility": "Brazil"
                },
                {
                    "LotCode": "VietnamLot",
                    "TotalQuantity": 5,
                    "StartDate": today,
                    "IndustrialFacility": "Vietnam"
                }
            ]
        }
        return order
    
    async def send_test_order(self):
        """Send a test order to the 'mokametrics.order' topic"""
        if not self.producer:
            logger.error("Producer not initialized")
            return False

        try:
            order = self.create_test_order()

            # Send to the 'mokametrics.order' topic
            await self.producer.send_and_wait(
                topic="mokametrics.order",
                key=order["Customer"],
                value=order
            )

            logger.info(f"Sent test order for customer {order['Customer']} with {len(order['Lots'])} lots")
            logger.info(f"Order details: {json.dumps(order, indent=2)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test order: {e}")
            return False

async def main():
    """Main test function"""
    sender = OrderTestSender()
    
    try:
        await sender.start()
        
        # Send a test order
        success = await sender.send_test_order()
        
        if success:
            logger.info("Test order sent successfully!")
            logger.info("Check the simulator logs to see if the lots were created correctly.")
        else:
            logger.error("Failed to send test order")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await sender.stop()

if __name__ == "__main__":
    asyncio.run(main())
