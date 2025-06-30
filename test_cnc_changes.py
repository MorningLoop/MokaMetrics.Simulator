#!/usr/bin/env python3
"""
Test script to verify that all cnc_milling to cnc changes work correctly
"""

import asyncio
import yaml
import logging
from datetime import datetime
from Simulator.state_machine import ProductionCoordinator, ProductionStage
from Simulator.Machine import get_machine_simulator
from Simulator.models import Location

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_config_loading():
    """Test that config.yaml loads correctly with cnc instead of cnc_milling"""
    logger.info("Testing config.yaml loading...")
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Check machine configuration
    machines = config.get('machines', {})
    for location, machine_counts in machines.items():
        assert 'cnc' in machine_counts, f"Location {location} should have 'cnc' machines"
        assert 'cnc_milling' not in machine_counts, f"Location {location} should not have 'cnc_milling' machines"
        logger.info(f"✓ {location}: {machine_counts['cnc']} CNC machines")
    
    # Check processing times
    processing_times = config.get('processing_times', {})
    assert 'cnc' in processing_times, "Processing times should have 'cnc' entry"
    assert 'cnc_milling' not in processing_times, "Processing times should not have 'cnc_milling' entry"
    logger.info(f"✓ CNC processing times: {processing_times['cnc']}")
    
    logger.info("✅ Config loading test passed!")
    return config

def test_production_stages():
    """Test that ProductionStage enum uses CNC instead of CNC_MILLING"""
    logger.info("Testing ProductionStage enum...")
    
    # Check that CNC stage exists
    assert hasattr(ProductionStage, 'CNC'), "ProductionStage should have CNC attribute"
    assert ProductionStage.CNC.value == "cnc", "ProductionStage.CNC should have value 'cnc'"
    
    # Check that CNC_MILLING stage doesn't exist
    assert not hasattr(ProductionStage, 'CNC_MILLING'), "ProductionStage should not have CNC_MILLING attribute"
    
    logger.info(f"✓ ProductionStage.CNC = {ProductionStage.CNC.value}")
    logger.info("✅ ProductionStage test passed!")

def test_machine_creation():
    """Test that machines can be created with 'cnc' type"""
    logger.info("Testing machine creation...")
    
    # Test CNC machine creation
    cnc_sim = get_machine_simulator('cnc_test_1', 'cnc', 'Italy')
    assert cnc_sim is not None, "CNC machine simulator should be created"
    logger.info(f"✓ CNC machine created: {type(cnc_sim).__name__}")
    
    # Test that fresa_cnc still works (backward compatibility)
    fresa_sim = get_machine_simulator('fresa_test_1', 'fresa_cnc', 'Italy')
    assert fresa_sim is not None, "Fresa CNC machine simulator should be created"
    logger.info(f"✓ Fresa CNC machine created: {type(fresa_sim).__name__}")
    
    logger.info("✅ Machine creation test passed!")

async def test_production_coordinator():
    """Test that ProductionCoordinator works with new cnc configuration"""
    logger.info("Testing ProductionCoordinator...")
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create production coordinator
    coordinator = ProductionCoordinator(None)
    
    # Initialize machines
    await coordinator.initialize_machines(config['machines'])
    
    # Check that CNC machines were created
    cnc_machines = coordinator.machine_pool.machines.get('cnc', [])
    assert len(cnc_machines) > 0, "Should have CNC machines"
    logger.info(f"✓ Created {len(cnc_machines)} CNC machines")
    
    # Check that stage mapping works
    assert ProductionStage.CNC in coordinator.stage_to_machine, "Stage to machine mapping should include CNC"
    assert coordinator.stage_to_machine[ProductionStage.CNC] == "cnc", "CNC stage should map to 'cnc' machine type"
    logger.info(f"✓ Stage mapping: {ProductionStage.CNC} -> {coordinator.stage_to_machine[ProductionStage.CNC]}")
    
    # Check processing times
    assert "cnc" in coordinator.processing_times, "Processing times should include 'cnc'"
    logger.info(f"✓ CNC processing times: {coordinator.processing_times['cnc']}")
    
    logger.info("✅ ProductionCoordinator test passed!")

async def test_stage_transitions():
    """Test that stage transitions work correctly with CNC"""
    logger.info("Testing stage transitions...")
    
    coordinator = ProductionCoordinator(None)
    
    # Test stage transitions
    next_stage = coordinator._get_next_stage(ProductionStage.QUEUED)
    assert next_stage == ProductionStage.CNC, f"QUEUED should transition to CNC, got {next_stage}"
    logger.info(f"✓ QUEUED -> {next_stage.value}")
    
    next_stage = coordinator._get_next_stage(ProductionStage.CNC)
    assert next_stage == ProductionStage.LATHE, f"CNC should transition to LATHE, got {next_stage}"
    logger.info(f"✓ CNC -> {next_stage.value}")
    
    # Test processing stage mapping
    processing_stage = coordinator._get_processing_stage(ProductionStage.CNC)
    assert processing_stage == ProductionStage.CNC, f"CNC queue should process as CNC, got {processing_stage}"
    logger.info(f"✓ CNC queue processes as {processing_stage.value}")
    
    # Test next production stage
    next_prod_stage = coordinator._get_next_production_stage(ProductionStage.CNC)
    assert next_prod_stage == ProductionStage.LATHE, f"CNC should complete to LATHE, got {next_prod_stage}"
    logger.info(f"✓ CNC completes to {next_prod_stage.value}")
    
    logger.info("✅ Stage transitions test passed!")

async def run_all_tests():
    """Run all tests"""
    logger.info("🧪 Starting comprehensive CNC changes test...")
    logger.info("=" * 50)
    
    try:
        # Test configuration
        config = test_config_loading()
        logger.info("")
        
        # Test production stages
        test_production_stages()
        logger.info("")
        
        # Test machine creation
        test_machine_creation()
        logger.info("")
        
        # Test production coordinator
        await test_production_coordinator()
        logger.info("")
        
        # Test stage transitions
        await test_stage_transitions()
        logger.info("")
        
        logger.info("=" * 50)
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ cnc_milling -> cnc changes are working correctly!")
        logger.info("")
        logger.info("Summary of changes verified:")
        logger.info("  ✓ config.yaml: cnc_milling -> cnc")
        logger.info("  ✓ ProductionStage: CNC_MILLING -> CNC")
        logger.info("  ✓ Machine creation: 'cnc' type works")
        logger.info("  ✓ Stage transitions: CNC stage flows correctly")
        logger.info("  ✓ Processing times: 'cnc' configuration works")
        logger.info("  ✓ Machine pool: CNC machines created successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_all_tests())
