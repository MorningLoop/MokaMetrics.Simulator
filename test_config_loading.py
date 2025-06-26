#!/usr/bin/env python3
"""
Test script to debug config loading issue
"""

import os
import sys
import yaml

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from Simulator.main import load_config

def test_config_loading():
    """Test what configuration is actually being loaded"""
    print("🧪 Testing Configuration Loading")
    print("=" * 50)
    
    # Check if config.yaml exists
    config_path = "config.yaml"
    print(f"📁 Config file path: {config_path}")
    print(f"📁 Config file exists: {os.path.exists(config_path)}")
    
    if os.path.exists(config_path):
        print("\n📄 Raw config.yaml content:")
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
            print(f"   health_check section: {raw_config.get('health_check', 'MISSING')}")
    
    # Test the load_config function
    print("\n⚙️  Testing load_config() function:")
    config = load_config()
    
    print(f"   health_check section: {config.get('health_check', 'MISSING')}")
    if 'health_check' in config:
        print(f"   health_check port: {config['health_check'].get('port', 'MISSING')}")
    
    # Check environment variables
    print("\n🌍 Environment variables:")
    print(f"   HEALTH_CHECK_PORT: {os.getenv('HEALTH_CHECK_PORT', 'NOT SET')}")
    print(f"   CONFIG_PATH: {os.getenv('CONFIG_PATH', 'NOT SET')}")
    
    # Test what port would actually be used
    print("\n🔌 Port resolution:")
    health_check_config = config.get('health_check', {})
    actual_port = health_check_config.get('port', 8080)
    print(f"   Actual port that would be used: {actual_port}")
    
    print("\n" + "=" * 50)
    if actual_port == 8083:
        print("✅ Configuration is correct - should use port 8083")
    elif actual_port == 8082:
        print("❌ Configuration shows port 8082 - this is the conflict!")
    elif actual_port == 8080:
        print("⚠️  Configuration shows default port 8080 - config.yaml not loaded?")
    else:
        print(f"❓ Configuration shows unexpected port {actual_port}")

if __name__ == "__main__":
    test_config_loading()
