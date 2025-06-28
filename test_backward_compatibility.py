#!/usr/bin/env python3
"""
Test script to verify backward compatibility with the old order message format
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
    """Test processor that mimics the order processing logic"""
    
    def __init__(self):
        self.received_lots = []
        
    async def process_order(self, order_data: Dict[str, Any]):
        """Process an order and create individual lots - same logic as kafka_integration.py"""
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

def create_legacy_order() -> dict:
    """Create a test order with the legacy format"""
    today = datetime.now().strftime("%Y-%m-%d")
    deadline = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    
    order = {
        "CustomerId": 5,
        "QuantityMachines": 15,
        "OrderDate": today,
        "Deadline": deadline,
        "Lots": [
            {
                "LotCode": "LegacyCode1",
                "TotalQuantity": 10,
                "StartDate": today,
                "IndustrialFacilityId": 1  # Italy
            },
            {
                "LotCode": "LegacyCode2",
                "TotalQuantity": 8,
                "StartDate": today,
                "IndustrialFacilityId": 2  # Brazil
            },
            {
                "LotCode": "LegacyCode3",
                "TotalQuantity": 12,
                "StartDate": today,
                "IndustrialFacilityId": 3  # Vietnam
            }
        ]
    }
    return order

def create_new_order() -> dict:
    """Create a test order with the new format"""
    today = datetime.now().strftime("%Y-%m-%d")
    deadline = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    
    order = {
        "Customer": "Monster Caffeine LLC",
        "QuantityMachines": 10,
        "OrderDate": today,
        "Deadline": deadline,
        "Lots": [
            {
                "LotCode": "NewCode1",
                "TotalQuantity": 5,
                "StartDate": today,
                "IndustrialFacility": "Italy"
            },
            {
                "LotCode": "NewCode2",
                "TotalQuantity": 7,
                "StartDate": today,
                "IndustrialFacility": "Brazil"
            },
            {
                "LotCode": "NewCode3",
                "TotalQuantity": 6,
                "StartDate": today,
                "IndustrialFacility": "Vietnam"
            }
        ]
    }
    return order

async def test_backward_compatibility():
    """Test both legacy and new order formats"""
    logger.info("Testing backward compatibility...")
    
    # Test legacy format
    logger.info("\n=== Testing Legacy Format ===")
    processor = OrderProcessor()
    legacy_order = create_legacy_order()
    logger.info(f"Legacy order: {json.dumps(legacy_order, indent=2)}")
    
    await processor.process_order(legacy_order)
    
    # Verify legacy results
    assert len(processor.received_lots) == 3, f"Expected 3 lots, got {len(processor.received_lots)}"
    
    expected_legacy = {
        "LegacyCode1": ("Italy", 10, "Customer_5"),
        "LegacyCode2": ("Brazil", 8, "Customer_5"),
        "LegacyCode3": ("Vietnam", 12, "Customer_5")
    }
    
    for lot in processor.received_lots:
        lot_code = lot["lot_code"]
        expected_location, expected_quantity, expected_customer = expected_legacy[lot_code]
        
        assert lot["location"] == expected_location, f"Legacy {lot_code}: expected {expected_location}, got {lot['location']}"
        assert lot["quantity"] == expected_quantity, f"Legacy {lot_code}: expected {expected_quantity}, got {lot['quantity']}"
        assert lot["customer"] == expected_customer, f"Legacy {lot_code}: expected {expected_customer}, got {lot['customer']}"
        
        logger.info(f"✓ Legacy lot {lot_code}: {lot['quantity']} pieces at {lot['location']} for {lot['customer']}")
    
    # Test new format
    logger.info("\n=== Testing New Format ===")
    processor = OrderProcessor()
    new_order = create_new_order()
    logger.info(f"New order: {json.dumps(new_order, indent=2)}")
    
    await processor.process_order(new_order)
    
    # Verify new results
    assert len(processor.received_lots) == 3, f"Expected 3 lots, got {len(processor.received_lots)}"
    
    expected_new = {
        "NewCode1": ("Italy", 5, "Monster Caffeine LLC"),
        "NewCode2": ("Brazil", 7, "Monster Caffeine LLC"),
        "NewCode3": ("Vietnam", 6, "Monster Caffeine LLC")
    }
    
    for lot in processor.received_lots:
        lot_code = lot["lot_code"]
        expected_location, expected_quantity, expected_customer = expected_new[lot_code]
        
        assert lot["location"] == expected_location, f"New {lot_code}: expected {expected_location}, got {lot['location']}"
        assert lot["quantity"] == expected_quantity, f"New {lot_code}: expected {expected_quantity}, got {lot['quantity']}"
        assert lot["customer"] == expected_customer, f"New {lot_code}: expected {expected_customer}, got {lot['customer']}"
        
        logger.info(f"✓ New lot {lot_code}: {lot['quantity']} pieces at {lot['location']} for {lot['customer']}")
    
    logger.info("\n✅ All backward compatibility tests passed!")
    logger.info("🎉 Both legacy and new order formats work correctly!")

if __name__ == "__main__":
    asyncio.run(test_backward_compatibility())
