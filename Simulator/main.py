"""
CoffeeMek S.p.A. - Production Simulator Main Entry Point
Coordinates production flow through state machine
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any
import yaml
import os

from .kafka_integration import KafkaDataSender, HealthCheckServer
from .state_machine import ProductionCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoffeeMekSimulator:
    """Main simulator class that coordinates everything"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.kafka_sender = KafkaDataSender(config)
        self.production_coordinator = ProductionCoordinator(self.kafka_sender)
        self.health_server = HealthCheckServer(
            config.get("health_check", {}).get("port", 8080),
            kafka_sender=self.kafka_sender
        )
        self.running = False
        
        # Set callback for new lots
        self.kafka_sender.set_lot_callback(self.production_coordinator.add_lot)

    async def add_lot(self, lot_data: Dict[str, Any]):
        """Add a lot manually to the production system"""
        if not self.running:
            raise RuntimeError("Simulator is not running")

        # Validate required fields
        required_fields = ["codice_lotto", "cliente", "quantita", "location"]
        for field in required_fields:
            if field not in lot_data:
                raise ValueError(f"Missing required field: {field}")

        # Add the lot to the production coordinator
        await self.production_coordinator.add_lot(lot_data)
        logger.info(f"Manually added lot: {lot_data['codice_lotto']}")
    
    async def start(self):
        """Start all components"""
        logger.info("Starting CoffeeMek Production Simulator...")
        
        # Start Kafka connections
        await self.kafka_sender.start()
        
        # Start health check server
        await self.health_server.start()
        
        # Initialize machines from config
        machine_config = self.config.get("machines", {
            "Italia": {"fresa_cnc": 1, "tornio": 1, "linea_assemblaggio": 1, "linea_test": 1},
            "Brasile": {"fresa_cnc": 1, "tornio": 1, "linea_assemblaggio": 1, "linea_test": 1},
            "Vietnam": {"fresa_cnc": 1, "tornio": 1, "linea_assemblaggio": 1, "linea_test": 1}
        })
        self.production_coordinator.initialize_machines(machine_config)
        
        self.running = True
        
        # Start concurrent tasks
        tasks = [
            asyncio.create_task(self.kafka_sender.consume_lots()),
            asyncio.create_task(self.production_coordinator.start()),
            asyncio.create_task(self._status_reporter())
        ]
        
        logger.info("All components started successfully")
        logger.info(f"Kafka broker: {self.kafka_sender.kafka_broker}")
        logger.info(f"Consuming lots from: coffeemek.orders.new_lots")
        logger.info(f"Sending telemetry to: coffeemek.telemetry.*")
        logger.info(f"Health check available at: http://localhost:{self.health_server.port}/health")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled, shutting down...")
    
    async def stop(self):
        """Stop all components"""
        logger.info("Stopping CoffeeMek Production Simulator...")
        self.running = False
        
        # Stop components
        await self.production_coordinator.stop()
        await self.kafka_sender.stop()
        await self.health_server.stop()
        
        logger.info("All components stopped")
    
    async def _status_reporter(self):
        """Periodically report production status"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                status = self.production_coordinator.get_status()
                logger.info(f"Production Status: {status['active_lots']} active lots")
                
                # Log queue sizes
                for stage, info in status['queues'].items():
                    if info['size'] > 0:
                        logger.info(f"  {stage}: {info['size']} lots waiting")
                
                # Update health server metrics
                self.health_server.message_count = sum(
                    info['size'] for info in status['queues'].values()
                )
                
            except Exception as e:
                logger.error(f"Error in status reporter: {e}")

def load_config() -> Dict[str, Any]:
    """Load configuration from file or environment"""
    # Default configuration with hardcoded Kafka broker
    config = {
        "kafka": {
            "bootstrap_servers": "165.227.168.240:9093"
        },
        "api": {
            "endpoint_url": "https://mokametrics-api-fafshjgtf4degege.italynorth-01.azurewebsites.net",
            "api_key": os.getenv("MOKAMETRICS_API_KEY", ""),
            "enable_api": os.getenv("ENABLE_API", "false").lower() == "true"
        },
        "health_check": {
            "port": int(os.getenv("HEALTH_CHECK_PORT", "8080"))
        }
    }
    
    # Try to load from config.yaml if exists
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                # Merge file config with defaults (file config takes precedence)
                def deep_merge(base, override):
                    for key, value in override.items():
                        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                            deep_merge(base[key], value)
                        else:
                            base[key] = value
                if file_config:
                    deep_merge(config, file_config)
        except Exception as e:
            logger.warning(f"Could not load config.yaml: {e}, using defaults")
    
    return config

async def main():
    """Main function"""
    config = load_config()
    simulator = CoffeeMekSimulator(config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, shutting down...")
        asyncio.create_task(simulator.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await simulator.start()
    except KeyboardInterrupt:
        await simulator.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await simulator.stop()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())