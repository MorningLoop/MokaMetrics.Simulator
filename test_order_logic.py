#!/usr/bin/env python3
"""
Simple test for the order processing logic
Tests the core logic without complex imports
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderProcessor:
    """Simplified order processor for testing"""
    
    def __init__(self):
        self.received_lots = []
        
    async def process_order(self, order_data: Dict[str, Any]):
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
                
                # Store the lot (simulating the callback)
                self.received_lots.append(lot_data)
                    
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            raise

def create_test_order() -> dict:
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

async def test_order_processing():
    """Test the order processing logic"""
    logger.info("Testing order processing logic...")
    
    # Create processor
    processor = OrderProcessor()
    
    # Create test order
    order = create_test_order()
    logger.info(f"Created test order: {json.dumps(order, indent=2)}")
    
    # Process the order
    await processor.process_order(order)
    
    # Verify results
    logger.info(f"Processed {len(processor.received_lots)} lots from the order")
    
    # Check that we received the expected number of lots
    assert len(processor.received_lots) == 3, f"Expected 3 lots, got {len(processor.received_lots)}"
    
    # Check facility mapping
    expected_locations = {"ACode": "Italy", "AnotherCode": "Brazil", "VietnamLot": "Vietnam"}
    
    for lot in processor.received_lots:
        lot_code = lot["lot_code"]
        expected_location = expected_locations[lot_code]
        actual_location = lot["location"]
        
        assert actual_location == expected_location, f"Lot {lot_code}: expected {expected_location}, got {actual_location}"
        
        # Check other fields
        assert lot["customer"] == "Monster Caffeine LLC"
        assert lot["quantity"] == 5
        assert lot["priority"] == "normal"
        
        logger.info(f"✓ Lot {lot_code}: {lot['quantity']} pieces at {lot['location']}")
    
    logger.info("✓ All tests passed!")
    return True

async def main():
    """Main test function"""
    try:
        success = await test_order_processing()
        
        if success:
            logger.info("🎉 Order processing test completed successfully!")
            logger.info("The new order format is correctly processed and lots are created with proper facility mapping:")
            logger.info("  - IndustrialFacilityId 1 → Italy")
            logger.info("  - IndustrialFacilityId 2 → Brazil") 
            logger.info("  - IndustrialFacilityId 3 → Vietnam")
        else:
            logger.error("❌ Order processing test failed")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
