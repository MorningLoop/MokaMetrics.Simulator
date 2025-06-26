#!/usr/bin/env python3
"""
Test script to verify that lots respect their quantity and continue processing until complete
"""

import asyncio
import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from Simulator.state_machine import ProductionLot, ProductionStage

def test_quantity_processing():
    """Test that lots track pieces produced correctly"""
    print("🧪 Testing Quantity-Based Processing")
    print("=" * 60)
    
    # Test ProductionLot quantity tracking
    print("📦 Testing ProductionLot quantity tracking:")
    
    # Create a test lot with quantity 10
    lot = ProductionLot(
        lot_code="TEST-QTY-001",
        customer="Test Customer",
        quantity=10,
        location="Italy"
    )
    
    print(f"   Created lot: {lot.lot_code}")
    print(f"   Target quantity: {lot.quantity}")
    print(f"   Initial pieces produced: {lot.pieces_produced}")
    print(f"   Remaining pieces: {lot.get_remaining_pieces()}")
    print(f"   Is complete: {lot.is_quantity_complete()}")
    
    # Simulate production cycles
    print("\n🔄 Simulating production cycles:")
    
    cycle = 1
    while not lot.is_quantity_complete():
        # Simulate producing 1-3 pieces per cycle
        pieces_this_cycle = min(3, lot.get_remaining_pieces())
        lot.add_pieces_produced(pieces_this_cycle)
        
        print(f"   Cycle {cycle}: Produced {pieces_this_cycle} pieces. Total: {lot.pieces_produced}/{lot.quantity}")
        
        if lot.is_quantity_complete():
            print(f"   ✅ Lot {lot.lot_code} completed after {cycle} cycles!")
            break
        
        cycle += 1
        
        # Safety check to prevent infinite loop
        if cycle > 20:
            print("   ❌ Too many cycles - something is wrong!")
            break
    
    # Test edge cases
    print("\n🧪 Testing edge cases:")
    
    # Test lot with quantity 1
    small_lot = ProductionLot(
        lot_code="SMALL-001",
        customer="Small Customer", 
        quantity=1,
        location="Brazil"
    )
    
    print(f"   Small lot quantity: {small_lot.quantity}")
    small_lot.add_pieces_produced(1)
    print(f"   After producing 1 piece: {small_lot.is_quantity_complete()}")
    
    # Test lot with large quantity
    large_lot = ProductionLot(
        lot_code="LARGE-001",
        customer="Large Customer",
        quantity=100,
        location="Vietnam"
    )
    
    print(f"   Large lot quantity: {large_lot.quantity}")
    large_lot.add_pieces_produced(50)
    print(f"   After producing 50 pieces: {large_lot.pieces_produced}/{large_lot.quantity}")
    print(f"   Remaining: {large_lot.get_remaining_pieces()}")
    print(f"   Is complete: {large_lot.is_quantity_complete()}")
    
    print("\n" + "=" * 60)
    print("✅ Quantity processing test completed!")
    
    print("\n📋 How the new logic works:")
    print("   1. Each lot tracks pieces_produced vs target quantity")
    print("   2. Machines produce 1-15 pieces per cycle (varies by type)")
    print("   3. Lots stay in current stage until quantity is complete")
    print("   4. Only then do they move to the next production stage")
    print("   5. Pieces counter resets when moving to new stage")
    
    print("\n🎯 Expected behavior in simulator:")
    print("   • Lot with quantity=50 will cycle multiple times per stage")
    print("   • Each machine cycle produces some pieces toward the total")
    print("   • Lot progresses: CNC(50) → Lathe(50) → Assembly(50) → Test(50)")
    print("   • Total production time scales with lot quantity")

if __name__ == "__main__":
    test_quantity_processing()
