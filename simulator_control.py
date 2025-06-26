#!/usr/bin/env python3
"""
MokaMetrics Simulator Control Launcher
Provides both console and web interfaces for simulator control
"""

import argparse
import asyncio
import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    parser = argparse.ArgumentParser(
        description="MokaMetrics Simulator Control Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s console          # Start console interface (default)
  %(prog)s web              # Start web interface
  %(prog)s web --port 8080  # Start web interface on port 8080
  %(prog)s --help           # Show this help message

Features:
  - Accelerated processing (5-minute total cycles)
  - High-frequency telemetry (1-second intervals)
  - Real-time monitoring and statistics
  - Start/stop simulator control
  - Kafka topic monitoring
  - Machine utilization tracking
        """
    )
    
    parser.add_argument(
        'interface',
        choices=['console', 'web'],
        nargs='?',
        default='console',
        help='Interface type to launch (default: console)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8081,
        help='Port for web interface (default: 8081)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host for web interface (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='MokaMetrics Simulator Control v1.0'
    )
    
    args = parser.parse_args()
    
    print("🏭 MokaMetrics Simulator Control")
    print("=" * 40)
    print("Testing Mode Configuration:")
    print("  • Accelerated processing: 1-2 minutes per stage")
    print("  • Total cycle time: ~5 minutes")
    print("  • High-frequency telemetry: 1-second intervals")
    print("  • Real-time monitoring enabled")
    print()
    
    if args.interface == 'console':
        print("🎮 Starting Console Interface...")
        print("Features:")
        print("  • Real-time dashboard with rich formatting")
        print("  • Live statistics and machine status")
        print("  • Automatic refresh every 0.5 seconds")
        print("  • Press Ctrl+C to stop")
        print()
        
        try:
            from Simulator.console_interface import main as console_main
            asyncio.run(console_main())
        except ImportError as e:
            print(f"❌ Error importing console interface: {e}")
            print("Make sure all dependencies are installed:")
            print("  pip install rich aiokafka")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error starting console interface: {e}")
            sys.exit(1)
    
    elif args.interface == 'web':
        print(f"🌐 Starting Web Interface on {args.host}:{args.port}...")
        print("Features:")
        print("  • Browser-based control panel")
        print("  • Real-time WebSocket updates")
        print("  • Start/stop simulator controls")
        print("  • Responsive design for mobile/desktop")
        print(f"  • Access at: http://{args.host}:{args.port}")
        print()
        
        try:
            # Import the web interface
            try:
                from Simulator.web_interface import WebInterface
            except ImportError as e:
                print(f"❌ Error importing web interface: {e}")
                print("Make sure all dependencies are installed:")
                print("  pip install aiokafka aiohttp aiohttp-cors")
                sys.exit(1)

            async def run_web():
                try:
                    interface = WebInterface(host=args.host, port=args.port)
                    runner = await interface.start_server()

                    # Keep running until interrupted
                    while True:
                        await asyncio.sleep(1)

                except KeyboardInterrupt:
                    print("\n🛑 Shutting down web interface...")
                    if 'interface' in locals() and 'runner' in locals():
                        await interface.stop_server(runner)
                except Exception as e:
                    print(f"❌ Error in web interface: {e}")
                    raise

            asyncio.run(run_web())

        except Exception as e:
            print(f"❌ Error starting web interface: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
