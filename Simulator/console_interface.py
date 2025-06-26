"""
Console interface for MokaMetrics Simulator control and monitoring
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional
import threading
import time

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.columns import Columns
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' library not available. Install with: pip install rich")

from .monitoring import monitor
from .main import CoffeeMekSimulator, load_config

class ConsoleInterface:
    """Console interface for simulator control"""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.simulator: Optional[CoffeeMekSimulator] = None
        self.running = False
        self.display_task: Optional[asyncio.Task] = None

    def create_status_display(self) -> Layout:
        """Create the status display layout"""
        if not RICH_AVAILABLE:
            return None

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        return layout

    def update_display(self, layout: Layout):
        """Update the display with current statistics"""
        if not RICH_AVAILABLE or not layout:
            return
            
        stats = monitor.get_current_stats()
        
        # Header
        header_text = Text("🏭 MokaMetrics Simulator - Testing Mode", style="bold blue")
        header_panel = Panel(header_text, style="blue")
        layout["header"].update(header_panel)
        
        # Main content - left side
        # System stats
        system_table = Table(title="📊 System Statistics", show_header=True)
        system_table.add_column("Metric", style="cyan")
        system_table.add_column("Value", style="green")
        
        system_table.add_row("Uptime", stats["uptime_formatted"])
        system_table.add_row("Total Lots Completed", str(stats["total_lots_completed"]))
        system_table.add_row("Total Messages Sent", str(stats["total_messages_sent"]))
        system_table.add_row("Messages/Second", str(stats["messages_per_second"]))
        system_table.add_row("Messages/Minute", str(stats["messages_per_minute"]))
        system_table.add_row("Avg Cycle Time", f"{stats['average_cycle_time_minutes']:.2f} min")
        
        # Active lots
        lots_table = Table(title="📦 Active Lots", show_header=True)
        lots_table.add_column("Lot Code", style="yellow")
        lots_table.add_column("Customer", style="cyan")
        lots_table.add_column("Stage", style="green")
        lots_table.add_column("Location", style="blue")
        lots_table.add_column("Qty", style="magenta")
        
        for lot in stats["active_lots"][:10]:  # Show max 10 lots
            lots_table.add_row(
                lot["lot_code"],
                lot["customer"],
                lot["current_stage"],
                lot["location"],
                str(lot["quantity"])
            )
        
        layout["left"].split_column(
            Layout(Panel(system_table), name="system"),
            Layout(Panel(lots_table), name="lots")
        )
        
        # Main content - right side
        # Machine utilization
        machines_table = Table(title="🔧 Machine Utilization", show_header=True)
        machines_table.add_column("Machine ID", style="cyan")
        machines_table.add_column("Type", style="yellow")
        machines_table.add_column("Status", style="green")
        machines_table.add_column("Current Lot", style="blue")
        machines_table.add_column("Utilization %", style="red")
        
        for machine in stats["machine_utilization"]:
            status = "🟢 Busy" if machine["is_busy"] else "⚪ Idle"
            machines_table.add_row(
                machine["machine_id"],
                machine["machine_type"],
                status,
                machine["current_lot"] or "-",
                f"{machine['utilization_percentage']:.1f}%"
            )
        
        # Topic statistics
        topics_table = Table(title="📡 Kafka Topics", show_header=True)
        topics_table.add_column("Topic", style="cyan")
        topics_table.add_column("Total Sent", style="green")
        topics_table.add_column("Per Second", style="yellow")
        topics_table.add_column("Per Minute", style="blue")
        
        for topic, topic_stats in stats["topic_stats"].items():
            topics_table.add_row(
                topic.replace("mokametrics.", ""),
                str(topic_stats["total_sent"]),
                str(topic_stats["per_second"]),
                str(topic_stats["per_minute"])
            )
        
        layout["right"].split_column(
            Layout(Panel(machines_table), name="machines"),
            Layout(Panel(topics_table), name="topics")
        )
        
        # Footer
        footer_text = Text("Press Ctrl+C to stop simulator | A to add lot | Q to quit", style="dim")
        footer_panel = Panel(footer_text, style="dim")
        layout["footer"].update(footer_panel)
    
    async def add_lot_interactive(self):
        """Interactive lot addition"""
        if not RICH_AVAILABLE:
            # Simple text input for fallback
            print("\n--- Add New Lot ---")
            customer = input("Customer name (default: Test Customer): ").strip() or "Test Customer"
            quantity = input("Quantity (default: 100): ").strip() or "100"
            location = input("Location (Italy/Brazil/Vietnam, default: Italy): ").strip() or "Italy"

            try:
                quantity = int(quantity)
                if location not in ["Italy", "Brazil", "Vietnam"]:
                    print("❌ Invalid location. Using Italy.")
                    location = "Italy"

                await self._add_lot(customer, quantity, location)
            except ValueError:
                print("❌ Invalid quantity. Please enter a number.")
            return

        # Rich interface for lot addition
        from rich.prompt import Prompt, IntPrompt, Confirm

        try:
            customer = Prompt.ask("Customer name", default="Test Customer")
            quantity = IntPrompt.ask("Quantity", default=100)
            location = Prompt.ask("Location", choices=["Italy", "Brazil", "Vietnam"], default="Italy")

            await self._add_lot(customer, quantity, location)

        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                self.console.print("❌ Lot addition cancelled", style="yellow")
            else:
                print("❌ Lot addition cancelled")

    async def _add_lot(self, customer: str, quantity: int, location: str):
        """Add a lot to the simulator"""
        try:
            from datetime import datetime
            import random

            lot_data = {
                "lot_code": f"CONSOLE-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                "customer": customer,
                "quantity": quantity,
                "location": location,
                "priority": "normal",
                "timestamp": datetime.now().isoformat()
            }

            await self.simulator.add_lot(lot_data)

            if RICH_AVAILABLE:
                self.console.print(f"✅ Added lot {lot_data['lot_code']} for {customer}", style="green")
            else:
                print(f"✅ Added lot {lot_data['lot_code']} for {customer}")

        except Exception as e:
            if RICH_AVAILABLE:
                self.console.print(f"❌ Error adding lot: {e}", style="red")
            else:
                print(f"❌ Error adding lot: {e}")

    async def display_loop(self):
        """Main display update loop"""
        if not RICH_AVAILABLE:
            # Fallback to simple text display
            while self.running:
                stats = monitor.get_current_stats()
                print(f"\n--- MokaMetrics Simulator Status ---")
                print(f"Uptime: {stats['uptime_formatted']}")
                print(f"Active Lots: {len(stats['active_lots'])}")
                print(f"Completed Lots: {stats['total_lots_completed']}")
                print(f"Messages/sec: {stats['messages_per_second']}")
                print(f"Total Messages: {stats['total_messages_sent']}")
                print("Press 'a' + Enter to add lot, Ctrl+C to quit")
                await asyncio.sleep(2)
            return

        layout = self.create_status_display()

        with Live(layout, refresh_per_second=2, screen=True) as live:
            while self.running:
                try:
                    self.update_display(layout)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Display error: {e}")
                    await asyncio.sleep(1)
    
    async def start_simulator(self):
        """Start the simulator"""
        try:
            config = load_config()
            self.simulator = CoffeeMekSimulator(config)
            
            if RICH_AVAILABLE:
                self.console.print("🚀 Starting MokaMetrics Simulator...", style="bold green")
            else:
                print("🚀 Starting MokaMetrics Simulator...")
            
            # Start simulator in background
            simulator_task = asyncio.create_task(self.simulator.start())
            
            # Start display
            self.running = True
            self.display_task = asyncio.create_task(self.display_loop())
            
            # Wait for either to complete
            await asyncio.gather(simulator_task, self.display_task, return_exceptions=True)
            
        except Exception as e:
            if RICH_AVAILABLE:
                self.console.print(f"❌ Error starting simulator: {e}", style="bold red")
            else:
                print(f"❌ Error starting simulator: {e}")
    
    async def stop_simulator(self):
        """Stop the simulator"""
        self.running = False
        
        if self.display_task:
            self.display_task.cancel()
        
        if self.simulator:
            await self.simulator.stop()
        
        if RICH_AVAILABLE:
            self.console.print("🛑 Simulator stopped", style="bold red")
        else:
            print("🛑 Simulator stopped")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            if RICH_AVAILABLE:
                self.console.print("\n🛑 Received shutdown signal...", style="bold yellow")
            else:
                print("\n🛑 Received shutdown signal...")
            
            # Create new event loop for cleanup if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.create_task(self.stop_simulator())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main console interface entry point"""
    interface = ConsoleInterface()
    interface.setup_signal_handlers()
    
    if RICH_AVAILABLE:
        interface.console.print("🎮 MokaMetrics Simulator Console Interface", style="bold blue")
        interface.console.print("Starting in testing mode with accelerated processing...", style="yellow")
    else:
        print("🎮 MokaMetrics Simulator Console Interface")
        print("Starting in testing mode with accelerated processing...")
    
    try:
        await interface.start_simulator()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
