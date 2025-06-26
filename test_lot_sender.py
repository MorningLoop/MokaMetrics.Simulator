#!/usr/bin/env python3
"""
Test lot sender for CoffeeMek Production Simulator
Sends test lots to Kafka for processing by the simulator
"""

import asyncio
import json
import argparse
import random
from datetime import datetime, timezone
from typing import List, Dict, Any
from aiokafka import AIOKafkaProducer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestLotSender:
    """Sends test lots to Kafka for simulator testing"""
    
    def __init__(self, kafka_broker: str = "165.227.168.240:9093"):
        self.kafka_broker = kafka_broker
        self.producer = None
        self.topic = "coffeemek.orders.new_lots"
        
    async def start(self):
        """Initialize Kafka producer"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_broker,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        await self.producer.start()
        logger.info(f"Connected to Kafka broker: {self.kafka_broker}")
        
    async def stop(self):
        """Stop Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    def generate_test_lot(self, lot_number: int) -> Dict[str, Any]:
        """Generate a test lot with realistic data"""
        locations = ["Italy", "Brazil", "Vietnam"]
        priorities = ["normal", "high", "low"]
        clients = ["Acme Corp", "Global Coffee Ltd", "Premium Beans Inc", "Coffee Masters", "Bean & Co"]
        
        lot_code = f"L-2025-{lot_number:04d}"
        
        return {
            "lot_code": lot_code,
            "customer": random.choice(clients),
            "quantity": random.randint(50, 500),
            "location": random.choice(locations),
            "priority": random.choice(priorities),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def send_lot(self, lot_data: Dict[str, Any]) -> bool:
        """Send a single lot to Kafka"""
        try:
            await self.producer.send_and_wait(
                topic=self.topic,
                key=lot_data["lot_code"],
                value=lot_data
            )
            logger.info(f"Sent lot: {lot_data['lot_code']} to {lot_data['location']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send lot {lot_data['lot_code']}: {e}")
            return False
    
    async def send_batch(self, count: int) -> int:
        """Send a batch of test lots"""
        logger.info(f"Sending {count} test lots...")
        sent_count = 0
        
        for i in range(1, count + 1):
            lot_data = self.generate_test_lot(i)
            if await self.send_lot(lot_data):
                sent_count += 1
            
            # Small delay between lots
            await asyncio.sleep(0.1)
        
        logger.info(f"Successfully sent {sent_count}/{count} lots")
        return sent_count
    
    async def send_continuous(self, rate_per_minute: int, duration_minutes: int = None):
        """Send lots continuously at specified rate"""
        interval = 60.0 / rate_per_minute  # seconds between lots
        logger.info(f"Sending lots continuously at {rate_per_minute} lots/minute (every {interval:.1f}s)")
        
        if duration_minutes:
            logger.info(f"Will run for {duration_minutes} minutes")
        else:
            logger.info("Will run indefinitely (Ctrl+C to stop)")
        
        lot_counter = 1
        start_time = datetime.now()
        
        try:
            while True:
                if duration_minutes:
                    elapsed = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed >= duration_minutes:
                        break
                
                lot_data = self.generate_test_lot(lot_counter)
                await self.send_lot(lot_data)
                lot_counter += 1
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        
        logger.info(f"Sent {lot_counter - 1} lots total")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Send test lots to CoffeeMek simulator")
    parser.add_argument("--mode", choices=["batch", "continuous"], default="batch",
                       help="Sending mode: batch or continuous")
    parser.add_argument("--count", type=int, default=5,
                       help="Number of lots to send in batch mode")
    parser.add_argument("--rate", type=int, default=2,
                       help="Lots per minute in continuous mode")
    parser.add_argument("--duration", type=int,
                       help="Duration in minutes for continuous mode (default: infinite)")
    parser.add_argument("--broker", default="165.227.168.240:9093",
                       help="Kafka broker address")
    
    args = parser.parse_args()
    
    sender = TestLotSender(args.broker)
    
    try:
        await sender.start()
        
        if args.mode == "batch":
            await sender.send_batch(args.count)
        else:  # continuous
            await sender.send_continuous(args.rate, args.duration)
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await sender.stop()

if __name__ == "__main__":
    asyncio.run(main())
