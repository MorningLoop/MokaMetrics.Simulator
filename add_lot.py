#!/usr/bin/env python3
"""
Command-line tool to add lots to the MokaMetrics Simulator
"""

import argparse
import asyncio
import json
import sys
import random
from datetime import datetime
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, '.')

async def add_lot_via_api(host: str, port: int, lot_data: Dict[str, Any]) -> bool:
    """Add lot via web API"""
    try:
        import aiohttp
        
        url = f"http://{host}:{port}/api/add_lot"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=lot_data) as response:
                result = await response.json()
                
                if result.get("success"):
                    print(f"✅ {result.get('message', 'Lot added successfully')}")
                    return True
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
                    return False
                    
    except Exception as e:
        print(f"❌ Failed to connect to web interface: {e}")
        print(f"Make sure the web interface is running at {host}:{port}")
        return False

async def add_lot_directly(lot_data: Dict[str, Any]) -> bool:
    """Add lot directly to simulator (if running)"""
    try:
        from Simulator.main import load_config, CoffeeMekSimulator
        
        # This would require the simulator to be running in the same process
        # For now, we'll just show what would be sent
        print(f"📦 Lot data that would be added:")
        print(json.dumps(lot_data, indent=2))
        print("Note: Use the web API method when simulator is running")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def generate_lot_data(customer: str, quantity: int, location: str, priority: str) -> Dict[str, Any]:
    """Generate lot data"""
    timestamp = datetime.now()
    lot_code = f"CLI-{timestamp.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    
    return {
        "codice_lotto": lot_code,
        "cliente": customer,
        "quantita": quantity,
        "location": location,
        "priority": priority,
        "timestamp": timestamp.isoformat()
    }

async def add_multiple_lots(count: int, host: str, port: int, **lot_params) -> None:
    """Add multiple lots for testing"""
    customers = ["Lavazza", "Illy", "Segafredo", "Kimbo", "Bialetti", "Test Customer"]
    locations = ["Italia", "Brasile", "Vietnam"]
    priorities = ["normal", "high", "urgent"]
    
    success_count = 0
    
    for i in range(count):
        # Randomize parameters if not specified
        customer = lot_params.get("customer") or random.choice(customers)
        location = lot_params.get("location") or random.choice(locations)
        priority = lot_params.get("priority") or random.choice(priorities)
        quantity = lot_params.get("quantity") or random.randint(50, 200)
        
        lot_data = generate_lot_data(customer, quantity, location, priority)
        
        print(f"\n📦 Adding lot {i+1}/{count}: {lot_data['codice_lotto']}")
        print(f"   Customer: {customer}, Quantity: {quantity}, Location: {location}")
        
        if await add_lot_via_api(host, port, lot_data):
            success_count += 1
        
        # Small delay between lots
        if i < count - 1:
            await asyncio.sleep(0.5)
    
    print(f"\n📊 Summary: {success_count}/{count} lots added successfully")

async def main():
    parser = argparse.ArgumentParser(
        description="Add lots to MokaMetrics Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Add single lot with defaults
  %(prog)s --customer "Lavazza" --quantity 150  # Add specific lot
  %(prog)s --batch 5                          # Add 5 random lots
  %(prog)s --batch 10 --location "Italia"     # Add 10 lots in Italia
  %(prog)s --host localhost --port 8080       # Use custom web interface address

Locations: Italia, Brasile, Vietnam
Priorities: normal, high, urgent
        """
    )
    
    parser.add_argument(
        "--customer",
        default="Test Customer",
        help="Customer name (default: Test Customer)"
    )
    
    parser.add_argument(
        "--quantity",
        type=int,
        default=100,
        help="Quantity (default: 100)"
    )
    
    parser.add_argument(
        "--location",
        choices=["Italia", "Brasile", "Vietnam"],
        default="Italia",
        help="Location (default: Italia)"
    )
    
    parser.add_argument(
        "--priority",
        choices=["normal", "high", "urgent"],
        default="normal",
        help="Priority (default: normal)"
    )
    
    parser.add_argument(
        "--batch",
        type=int,
        help="Add multiple lots (specify count)"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Web interface host (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Web interface port (default: 8081)"
    )
    
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Add lot directly (for testing, shows data only)"
    )
    
    args = parser.parse_args()
    
    print("📦 MokaMetrics Simulator - Lot Addition Tool")
    print("=" * 50)
    
    # Validate quantity
    if args.quantity <= 0 or args.quantity > 1000:
        print("❌ Error: Quantity must be between 1 and 1000")
        sys.exit(1)
    
    try:
        if args.batch:
            # Add multiple lots
            print(f"🚀 Adding {args.batch} lots...")
            await add_multiple_lots(
                args.batch, args.host, args.port,
                customer=args.customer if args.customer != "Test Customer" else None,
                quantity=args.quantity if args.quantity != 100 else None,
                location=args.location if args.location != "Italia" else None,
                priority=args.priority if args.priority != "normal" else None
            )
        else:
            # Add single lot
            lot_data = generate_lot_data(args.customer, args.quantity, args.location, args.priority)
            
            print(f"📦 Adding lot: {lot_data['codice_lotto']}")
            print(f"   Customer: {args.customer}")
            print(f"   Quantity: {args.quantity}")
            print(f"   Location: {args.location}")
            print(f"   Priority: {args.priority}")
            
            if args.direct:
                await add_lot_directly(lot_data)
            else:
                success = await add_lot_via_api(args.host, args.port, lot_data)
                if not success:
                    sys.exit(1)
        
        print("\n✅ Done!")
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
