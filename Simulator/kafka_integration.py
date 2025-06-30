"""
Kafka integration for CoffeeMek simulator
Handles both consuming incoming lots and sending telemetry data
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
import aiohttp
from aiohttp import web
from .monitoring import monitor

logger = logging.getLogger(__name__)

class KafkaDataSender:
    """Data sender that pushes to Kafka topics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.kafka_producer = None
        self.kafka_consumer = None
        self.http_session = None
        self.kafka_broker = "165.227.168.240:29093"
        self.api_endpoint = "https://mokametrics-api-fafshjgtf4degege.italynorth-01.azurewebsites.net"
        self.lot_callback = None  # Callback for new lots
        
    async def start(self):
        """Start Kafka producer, consumer and HTTP session"""
        # Initialize Kafka producer
        try:
            self.kafka_producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k is not None else None,
                acks='all',  # Wait for all replicas to acknowledge
                compression_type='gzip'  # Compress messages
            )
            await self.kafka_producer.start()
            logger.info(f"Kafka producer started successfully. Connected to {self.kafka_broker}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
        
        # Initialize Kafka consumer for incoming orders
        try:
            self.kafka_consumer = AIOKafkaConsumer(
                'mokametrics.order',
                bootstrap_servers=self.kafka_broker,
                group_id='coffeemek-simulator',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',  # Start from latest messages
                enable_auto_commit=True
            )
            await self.kafka_consumer.start()
            logger.info("Kafka consumer started for incoming orders")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            # Consumer is optional, continue without it
            
        # Initialize HTTP session for API calls
        self.http_session = aiohttp.ClientSession()
        logger.info("HTTP session initialized")
        
    async def stop(self):
        """Clean up resources"""
        if self.kafka_producer:
            await self.kafka_producer.stop()
            logger.info("Kafka producer stopped")
        
        if self.kafka_consumer:
            await self.kafka_consumer.stop()
            logger.info("Kafka consumer stopped")
            
        if self.http_session:
            await self.http_session.close()
            logger.info("HTTP session closed")
    
    def set_lot_callback(self, callback):
        """Set callback function for new lots"""
        self.lot_callback = callback
    
    async def consume_lots(self):
        """Consume incoming order messages and create lots"""
        if not self.kafka_consumer:
            logger.warning("Kafka consumer not initialized, cannot consume orders")
            return

        logger.info("Starting to consume orders from Kafka")

        try:
            async for msg in self.kafka_consumer:
                try:
                    order_data = msg.value
                    # Support both new and old customer field formats
                    customer_info = order_data.get('Customer') or order_data.get('CustomerId', 'unknown')
                    logger.info(f"Received new order for customer {customer_info}")

                    # Process the order and create lots
                    await self._process_order(order_data)

                except Exception as e:
                    logger.error(f"Error processing order message: {e}")

        except Exception as e:
            logger.error(f"Error in consume_lots: {e}")

    async def _process_order(self, order_data: Dict[str, Any]):
        """Process an order and create individual lots"""
        try:
            # Map IndustrialFacilityId to location names (for backward compatibility)
            facility_id_to_location = {
                1: "Italy",
                2: "Brazil",
                3: "Vietnam"
            }

            # Map location names to facility IDs (for new format)
            location_to_facility_id = {
                "Italy": 1,
                "Brazil": 2,
                "Vietnam": 3
            }

            # Support both old and new message formats
            # New format: Customer (string), old format: CustomerId (int)
            customer = order_data.get("Customer")
            customer_id = order_data.get("CustomerId")

            # Use Customer field if available, otherwise fall back to CustomerId
            if customer:
                customer_name = customer
                # Extract or generate customer ID for internal use
                customer_id_for_internal = customer_id if customer_id else hash(customer) % 10000
            else:
                # Backward compatibility: use CustomerId
                customer_name = f"Customer_{customer_id}" if customer_id else "Unknown_Customer"
                customer_id_for_internal = customer_id

            order_date = order_data.get("OrderDate")
            deadline = order_data.get("Deadline")
            lots = order_data.get("Lots", [])

            logger.info(f"Processing order with {len(lots)} lots for customer {customer_name}")

            for lot_info in lots:
                # Extract lot information
                lot_code = lot_info.get("LotCode")
                total_quantity = lot_info.get("TotalQuantity")
                start_date = lot_info.get("StartDate")

                # Support both old and new facility formats
                # New format: IndustrialFacility (string), old format: IndustrialFacilityId (int)
                facility_name = lot_info.get("IndustrialFacility")
                facility_id = lot_info.get("IndustrialFacilityId")

                if facility_name:
                    # New format: use facility name directly
                    location = facility_name
                    # Map to facility ID for internal use
                    facility_id_for_internal = location_to_facility_id.get(facility_name, 1)  # Default to Italy
                elif facility_id:
                    # Old format: map facility ID to location name
                    location = facility_id_to_location.get(facility_id, "Italy")  # Default to Italy if unknown
                    facility_id_for_internal = facility_id
                else:
                    # Default values if neither is provided
                    location = "Italy"
                    facility_id_for_internal = 1

                # Create lot data in the format expected by the production coordinator
                lot_data = {
                    "lot_code": lot_code,
                    "codice_lotto": lot_code,  # Keep for backward compatibility
                    "customer": customer_name,
                    "cliente": customer_name,  # Keep for backward compatibility
                    "quantity": total_quantity,
                    "quantita": total_quantity,  # Keep for backward compatibility
                    "location": location,
                    "priority": "normal",  # Default priority
                    "priorita": "normal",  # Keep for backward compatibility
                    "order_date": order_date,
                    "deadline": deadline,
                    "start_date": start_date,
                    "facility_id": facility_id_for_internal,
                    "timestamp": datetime.utcnow().isoformat()
                }

                logger.info(f"Creating lot {lot_code} with {total_quantity} pieces at {location}")

                # Call the callback if set
                if self.lot_callback:
                    await self.lot_callback(lot_data)

        except Exception as e:
            logger.error(f"Error processing order: {e}")
            raise
    
    async def send_to_kafka(self, data: Dict[str, Any]) -> bool:
        """Send data to Kafka topic"""
        if not self.kafka_producer:
            logger.error("Kafka producer not initialized")
            return False

        try:

            # Use lot code as key for partitioning
            key = data.get("codice_lotto", None)

            # Send to Kafka
            await self.kafka_producer.send_and_wait(
                topic=topic,
                key=key,
                value=data
            )

            logger.info(f"Sent to Kafka topic '{topic}': {key}")
            return True

        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send to Kafka: {e}")
            return False

    async def send_telemetry_data(self, data: Dict[str, Any], machine_type: str) -> bool:
        """Send telemetry data to specific telemetry topic"""
        if not self.kafka_producer:
            logger.error("Kafka producer not initialized")
            return False

        try:
            # Map machine types to telemetry topics
            machine_type_mapping = {
                "fresa_cnc": "cnc",
                "tornio": "lathe",  # tornio maps to lathe
                "assemblaggio": "assembly",
                "test": "testing"
            }

            telemetry_type = machine_type_mapping.get(machine_type, machine_type)
            topic = f"mokametrics.telemetry.{telemetry_type}"

            # Use machine_id as the partition key (as per specification)
            key = data.get("machine_id", None)

            # Send to Kafka
            await self.kafka_producer.send_and_wait(
                topic=topic,
                key=key,
                value=data
            )

            logger.info(f"Sent telemetry data to topic '{topic}': {key}")
            monitor.record_message_sent(topic, key)
            return True

        except KafkaError as e:
            logger.error(f"Kafka telemetry error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send telemetry data: {e}")
            return False

    async def send_piece_completion_data(self, data: Dict[str, Any]) -> bool:
        """Send piece completion data to the lot_completion topic (sent for each completed piece)"""
        if not self.kafka_producer:
            logger.error("Kafka producer not initialized")
            return False

        try:
            # Correct topic for piece-by-piece completion tracking
            topic = "mokametrics.production.lot_completion"

            # Use lot code as key for partitioning (as per specification)
            key = data.get("lot_code", None)

            # Send to Kafka
            await self.kafka_producer.send_and_wait(
                topic=topic,
                key=key,
                value=data
            )

            logger.info(f"Sent piece completion data to topic '{topic}': {key} (piece {data.get('lot_produced_quantity', '?')}/{data.get('lot_total_quantity', '?')})")
            monitor.record_message_sent(topic, key)
            return True

        except KafkaError as e:
            logger.error(f"Kafka piece completion error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send piece completion data: {e}")
            return False


    
    async def send_to_api(self, data: Dict[str, Any]) -> bool:
        """Send data to MokaMetrics API endpoint"""
        if not self.http_session:
            logger.error("HTTP session not initialized")
            return False
            
        try:
            # Prepare API endpoint
            endpoint = f"{self.api_endpoint}/api/telemetry"
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.config.get("api_key", ""),
                "X-Machine-Type": data.get("macchina", "unknown"),
                "X-Location": data.get("luogo", "unknown")
            }
            
            # Add request ID for tracking
            headers["X-Request-ID"] = f"{data.get('codice_lotto', 'unknown')}_{datetime.utcnow().timestamp()}"
            
            async with self.http_session.post(
                endpoint,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    logger.info(f"API response: {response_data.get('message', 'Success')}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"API returned status {response.status}: {error_text}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("API request timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to send to API: {e}")
            return False
    
    async def send_data(self, data: Dict[str, Any]) -> bool:
        """Send data to Kafka (primary) and optionally to API"""
        # Send to Kafka (primary data pipeline)
        kafka_result = await self.send_to_kafka(data)
        
        # Optionally send to API if configured
        api_result = True
        if self.config.get("enable_api", False) and self.config.get("api_key"):
            api_result = await self.send_to_api(data)
        
        # Return True if Kafka send was successful (API is optional)
        if not kafka_result:
            logger.error(f"Failed to send data to Kafka: {data.get('codice_lotto', 'unknown')}")
        
        return kafka_result

class HealthCheckServer:
    """Health check HTTP server with Kafka status"""
    
    def __init__(self, port: int = 8080, kafka_sender: Optional[KafkaDataSender] = None):
        self.port = port
        self.kafka_sender = kafka_sender
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/ready', self.readiness_check)
        self.runner = None
        self.start_time = datetime.utcnow()
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = None
        
    async def health_check(self, request):
        """Liveness probe - is the service running?"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "kafka_broker": "165.227.168.240:29093"
        })
    
    async def readiness_check(self, request):
        """Readiness probe - is the service ready to accept traffic?"""
        checks = {
            "kafka": False,
            "overall": False
        }
        
        # Check Kafka connection
        if self.kafka_sender and self.kafka_sender.kafka_producer:
            try:
                # Check if producer is running
                checks["kafka"] = not self.kafka_sender.kafka_producer._closed
            except:
                checks["kafka"] = False
        
        checks["overall"] = checks["kafka"]
        
        status_code = 200 if checks["overall"] else 503
        
        return web.json_response(checks, status=status_code)
    
    async def metrics(self, request):
        """Prometheus-style metrics endpoint"""
        metrics_text = f"""# HELP coffeemek_messages_sent_total Total number of messages sent
# TYPE coffeemek_messages_sent_total counter
coffeemek_messages_sent_total {self.message_count}

# HELP coffeemek_errors_total Total number of errors
# TYPE coffeemek_errors_total counter
coffeemek_errors_total {self.error_count}

# HELP coffeemek_uptime_seconds Service uptime in seconds
# TYPE coffeemek_uptime_seconds gauge
coffeemek_uptime_seconds {(datetime.utcnow() - self.start_time).total_seconds()}

# HELP coffeemek_last_message_timestamp Last message timestamp
# TYPE coffeemek_last_message_timestamp gauge
coffeemek_last_message_timestamp {self.last_message_time.timestamp() if self.last_message_time else 0}
"""
        
        return web.Response(text=metrics_text, content_type='text/plain')
    
    def increment_message_count(self):
        """Increment the message counter"""
        self.message_count += 1
        self.last_message_time = datetime.utcnow()
    
    def increment_error_count(self):
        """Increment the error counter"""
        self.error_count += 1
    
    async def start(self):
        """Start the health check server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health check server started on port {self.port}")
    
    async def stop(self):
        """Stop the health check server"""
        if self.runner:
            await self.runner.cleanup()

# Retry logic for resilience
class RetryHandler:
    """Handle retries with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        return False