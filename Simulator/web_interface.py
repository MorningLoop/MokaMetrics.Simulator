"""
Web interface for MokaMetrics Simulator control and monitoring
"""

import asyncio
import json
import signal
import sys
from datetime import datetime
from typing import Optional, Set
import weakref
import logging

from aiohttp import web, WSMsgType

try:
    import aiohttp_cors
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

from .monitoring import monitor

logger = logging.getLogger(__name__)

class WebInterface:
    """Web interface for simulator control"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8081):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.simulator: Optional[CoffeeMekSimulator] = None
        self.websockets: Set[web.WebSocketResponse] = set()
        self.running = False
        self.broadcast_task: Optional[asyncio.Task] = None
        
        self.setup_routes()
        self.setup_cors()
    
    def setup_cors(self):
        """Setup CORS for web interface"""
        if CORS_AVAILABLE:
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })

            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)
        else:
            # Basic CORS headers without aiohttp_cors
            @web.middleware
            async def cors_handler(request, handler):
                response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                return response

            self.app.middlewares.append(cors_handler)
    
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_post('/api/start', self.start_simulator_handler)
        self.app.router.add_post('/api/stop', self.stop_simulator_handler)
        self.app.router.add_post('/api/add_lot', self.add_lot_handler)
        self.app.router.add_post('/api/start_processing', self.start_processing_handler)
        self.app.router.add_post('/api/machine_maintenance', self.machine_maintenance_handler)
        self.app.router.add_get('/api/machines', self.machines_handler)
        self.app.router.add_get('/api/status', self.status_handler)
        # Note: No static files needed - everything is embedded in HTML
    
    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MokaMetrics Simulator Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .controls { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { margin-top: 0; color: #2c3e50; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        .btn-start { background: #27ae60; color: white; }
        .btn-stop { background: #e74c3c; color: white; }
        .btn:disabled { background: #bdc3c7; cursor: not-allowed; }
        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .status.running { background: #d5f4e6; color: #27ae60; }
        .status.stopped { background: #fadbd8; color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .metric { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-label { font-size: 14px; color: #7f8c8d; }
        .connection-status { position: fixed; top: 10px; right: 10px; padding: 5px 10px; border-radius: 4px; }
        .connected { background: #d5f4e6; color: #27ae60; }
        .disconnected { background: #fadbd8; color: #e74c3c; }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">Connecting...</div>
    
    <div class="container">
        <div class="header">
            <h1>🏭 MokaMetrics Simulator Control Panel</h1>
            <p>Ultra Fast Testing Mode - 40-second total production cycles</p>
        </div>
        
        <div class="controls">
            <h3>Simulator Control</h3>
            <div class="status" id="simulatorStatus">Status: Unknown</div>
            <button class="btn btn-start" id="startBtn" onclick="startSimulator()">Start Simulator</button>
            <button class="btn btn-stop" id="stopBtn" onclick="stopSimulator()" disabled>Stop Simulator</button>
            <button class="btn btn-start" id="startProcessingBtn" onclick="startProcessing()" disabled>🚀 Start Processing Queued Lots</button>
        </div>

        <div class="controls">
            <h3>📦 Add New Lot</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 15px;">
                <div>
                    <label for="customer">Customer:</label>
                    <input type="text" id="customer" placeholder="Customer Name" value="Test Customer" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div>
                    <label for="quantity">Quantity:</label>
                    <input type="number" id="quantity" placeholder="100" value="100" min="1" max="1000" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div>
                    <label for="location">Location:</label>
                    <select id="location" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        <option value="Italy">Italy</option>
                        <option value="Brazil">Brazil</option>
                        <option value="Vietnam">Vietnam</option>
                    </select>
                </div>
                <div>
                    <label for="priority">Priority:</label>
                    <select id="priority" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        <option value="normal">Normal</option>
                        <option value="high">High</option>
                        <option value="urgent">Urgent</option>
                    </select>
                </div>
            </div>
            <button class="btn btn-start" id="addLotBtn" onclick="addLot()" disabled>Add Lot</button>
            <div id="addLotStatus" style="margin-top: 10px;"></div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>📊 System Statistics</h3>
                <div class="metric" id="uptime">--</div>
                <div class="metric-label">Uptime</div>
                <br>
                <div class="metric" id="totalLots">0</div>
                <div class="metric-label">Total Lots Completed</div>
                <br>
                <div class="metric" id="messagesPerSec">0</div>
                <div class="metric-label">Messages/Second</div>
            </div>
            
            <div class="stat-card">
                <h3>📦 Active Lots</h3>
                <div id="activeLots">No active lots</div>
            </div>
            
            <div class="stat-card">
                <h3>🔧 Machine Utilization</h3>
                <div id="machineStats">No machine data</div>
            </div>
            
            <div class="stat-card">
                <h3>🛠️ Machine Maintenance</h3>
                <div id="maintenanceControls">
                    <div style="margin-bottom: 10px;">
                        <label for="machineSelect">Select Machine:</label>
                        <select id="machineSelect" style="width: 100%; padding: 5px; margin: 5px 0;">
                            <option value="">Select a machine...</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <input type="text" id="maintenanceReason" placeholder="Maintenance reason..." style="width: 100%; padding: 5px;">
                    </div>
                    <button class="btn btn-start" id="startMaintenanceBtn" onclick="setMaintenance(true)" disabled>Start Maintenance</button>
                    <button class="btn btn-stop" id="stopMaintenanceBtn" onclick="setMaintenance(false)" disabled>Stop Maintenance</button>
                    <div id="maintenanceStatus" style="margin-top: 10px;"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>📡 Kafka Topics</h3>
                <div id="topicStats">No topic data</div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let simulatorRunning = false;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function() {
                document.getElementById('connectionStatus').textContent = 'Connected';
                document.getElementById('connectionStatus').className = 'connection-status connected';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDisplay(data);
            };
            
            ws.onclose = function() {
                document.getElementById('connectionStatus').textContent = 'Disconnected';
                document.getElementById('connectionStatus').className = 'connection-status disconnected';
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function updateDisplay(stats) {
            // Update system stats
            document.getElementById('uptime').textContent = stats.uptime_formatted || '--';
            document.getElementById('totalLots').textContent = stats.total_lots_completed || 0;
            document.getElementById('messagesPerSec').textContent = stats.messages_per_second || 0;
            
            // Update active lots
            const activeLots = stats.active_lots || [];
            const lotsHtml = activeLots.length > 0 ? 
                `<table><tr><th>Lot Code</th><th>Customer</th><th>Stage</th><th>Location</th></tr>` +
                activeLots.slice(0, 5).map(lot => 
                    `<tr><td>${lot.lot_code}</td><td>${lot.customer}</td><td>${lot.current_stage}</td><td>${lot.location}</td></tr>`
                ).join('') + '</table>' : 'No active lots';
            document.getElementById('activeLots').innerHTML = lotsHtml;
            
            // Update machine stats - only show relevant machines
            const machines = stats.machine_utilization || [];
            
            // Get locations of active lots
            const activeLocations = new Set(activeLots.map(lot => lot.location));
            
            // Filter machines to show only relevant ones
            const relevantMachines = machines.filter(machine => {
                return machine.is_busy || 
                       machine.utilization_percentage > 0 || 
                       activeLocations.has(machine.location) ||
                       activeLots.length === 0; // Show all if no active lots
            });
            
            const machinesHtml = relevantMachines.length > 0 ?
                `<table><tr><th>Machine</th><th>Status</th><th>Utilization</th></tr>` +
                relevantMachines.map(machine => 
                    `<tr><td>${machine.machine_id}</td><td>${machine.is_busy ? '🟢 Busy' : '⚪ Idle'}</td><td>${machine.utilization_percentage.toFixed(1)}%</td></tr>`
                ).join('') + '</table>' : 'No machine data';
            document.getElementById('machineStats').innerHTML = machinesHtml;
            
            // Update topic stats
            const topics = stats.topic_stats || {};
            const topicsHtml = Object.keys(topics).length > 0 ?
                `<table><tr><th>Topic</th><th>Total</th><th>/min</th></tr>` +
                Object.entries(topics).map(([topic, topicStats]) => 
                    `<tr><td>${topic.replace('mokametrics.', '')}</td><td>${topicStats.total_sent}</td><td>${topicStats.per_minute}</td></tr>`
                ).join('') + '</table>' : 'No topic data';
            document.getElementById('topicStats').innerHTML = topicsHtml;
        }
        
        async function startSimulator() {
            try {
                const response = await fetch('/api/start', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    simulatorRunning = true;
                    updateControlButtons();
                    updateStatus('running', 'Simulator is running');
                    await loadMachines();
                } else {
                    alert('Failed to start simulator: ' + result.error);
                }
            } catch (error) {
                alert('Error starting simulator: ' + error);
            }
        }
        
        async function stopSimulator() {
            try {
                const response = await fetch('/api/stop', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    simulatorRunning = false;
                    updateControlButtons();
                    updateStatus('stopped', 'Simulator is stopped');
                } else {
                    alert('Failed to stop simulator: ' + result.error);
                }
            } catch (error) {
                alert('Error stopping simulator: ' + error);
            }
        }

        async function startProcessing() {
            try {
                const response = await fetch('/api/start_processing', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    showAddLotStatus('success', `✅ ${result.message}`);
                } else {
                    showAddLotStatus('error', `❌ ${result.error}`);
                }
            } catch (error) {
                showAddLotStatus('error', `❌ Error: ${error.message}`);
            }
        }
        
        function updateControlButtons() {
            document.getElementById('startBtn').disabled = simulatorRunning;
            document.getElementById('stopBtn').disabled = !simulatorRunning;
            document.getElementById('addLotBtn').disabled = !simulatorRunning;
            document.getElementById('startProcessingBtn').disabled = !simulatorRunning;
            updateMaintenanceButtons();
        }

        async function addLot() {
            try {
                const customer = document.getElementById('customer').value.trim();
                const quantity = parseInt(document.getElementById('quantity').value);
                const location = document.getElementById('location').value;
                const priority = document.getElementById('priority').value;

                // Validate inputs
                if (!customer) {
                    showAddLotStatus('error', 'Customer name is required');
                    return;
                }

                if (isNaN(quantity) || quantity < 1 || quantity > 1000) {
                    showAddLotStatus('error', 'Quantity must be between 1 and 1000');
                    return;
                }

                // Show loading
                showAddLotStatus('info', 'Adding lot...');

                const response = await fetch('/api/add_lot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        customer: customer,
                        quantity: quantity,
                        location: location,
                        priority: priority
                    })
                });

                const result = await response.json();

                if (result.success) {
                    showAddLotStatus('success', `✅ ${result.message}`);
                    // Reset form to defaults
                    document.getElementById('customer').value = 'Test Customer';
                    document.getElementById('quantity').value = '100';
                    document.getElementById('location').value = 'Italy';
                    document.getElementById('priority').value = 'normal';
                } else {
                    showAddLotStatus('error', `❌ ${result.error}`);
                }
            } catch (error) {
                showAddLotStatus('error', `❌ Error: ${error.message}`);
            }
        }

        function showAddLotStatus(type, message) {
            const statusEl = document.getElementById('addLotStatus');
            statusEl.textContent = message;
            statusEl.className = type === 'success' ? 'status running' :
                               type === 'error' ? 'status stopped' :
                               'status';

            // Clear status after 5 seconds for success/info messages
            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    statusEl.textContent = '';
                    statusEl.className = '';
                }, 5000);
            }
        }
        
        function updateStatus(status, message) {
            const statusEl = document.getElementById('simulatorStatus');
            statusEl.textContent = 'Status: ' + message;
            statusEl.className = 'status ' + status;
        }

        async function setMaintenance(inMaintenance) {
            try {
                const machineSelect = document.getElementById('machineSelect');
                const reasonInput = document.getElementById('maintenanceReason');
                const machineId = machineSelect.value;
                const reason = reasonInput.value.trim() || (inMaintenance ? 'Manual maintenance' : '');

                if (!machineId) {
                    showMaintenanceStatus('error', 'Please select a machine');
                    return;
                }

                showMaintenanceStatus('info', inMaintenance ? 'Starting maintenance...' : 'Stopping maintenance...');

                const response = await fetch('/api/machine_maintenance', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        machine_id: machineId,
                        in_maintenance: inMaintenance,
                        reason: reason
                    })
                });

                const result = await response.json();

                if (result.success) {
                    showMaintenanceStatus('success', `✅ ${result.message}`);
                    if (!inMaintenance) {
                        reasonInput.value = '';
                    }
                    await loadMachines();
                } else {
                    showMaintenanceStatus('error', `❌ ${result.error}`);
                }
            } catch (error) {
                showMaintenanceStatus('error', `❌ Error: ${error.message}`);
            }
        }

        async function loadMachines() {
            try {
                if (!simulatorRunning) return;

                const response = await fetch('/api/machines');
                const result = await response.json();

                if (result.success) {
                    const select = document.getElementById('machineSelect');
                    select.innerHTML = '<option value="">Select a machine...</option>';

                    Object.values(result.machines).forEach(machine => {
                        const option = document.createElement('option');
                        option.value = machine.machine_id;
                        const status = machine.in_maintenance ? ' (MAINTENANCE)' : 
                                     machine.is_busy ? ' (BUSY)' : ' (AVAILABLE)';
                        option.textContent = `${machine.machine_id} - ${machine.machine_type} - ${machine.location}${status}`;
                        select.appendChild(option);
                    });

                    updateMaintenanceButtons();
                }
            } catch (error) {
                console.error('Error loading machines:', error);
            }
        }

        function updateMaintenanceButtons() {
            const machineSelect = document.getElementById('machineSelect');
            const startBtn = document.getElementById('startMaintenanceBtn');
            const stopBtn = document.getElementById('stopMaintenanceBtn');
            
            const machineSelected = machineSelect.value !== '';
            startBtn.disabled = !simulatorRunning || !machineSelected;
            stopBtn.disabled = !simulatorRunning || !machineSelected;
        }

        function showMaintenanceStatus(type, message) {
            const statusEl = document.getElementById('maintenanceStatus');
            statusEl.textContent = message;
            statusEl.className = type === 'success' ? 'status running' :
                               type === 'error' ? 'status stopped' :
                               'status';

            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    statusEl.textContent = '';
                    statusEl.className = '';
                }, 5000);
            }
        }
        
        // Initialize
        connectWebSocket();
        updateControlButtons();
        
        // Add event listener for machine select
        document.getElementById('machineSelect').addEventListener('change', updateMaintenanceButtons);
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info(f"WebSocket client connected. Total clients: {len(self.websockets)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.websockets)}")
        
        return ws
    
    async def start_simulator_handler(self, request):
        """Start the simulator"""
        try:
            if self.simulator and self.running:
                return web.json_response({"success": False, "error": "Simulator already running"})

            # Import simulator classes only when needed
            from .main import CoffeeMekSimulator, load_config

            config = load_config()
            self.simulator = CoffeeMekSimulator(config)
            self.running = True

            # Start simulator in background
            asyncio.create_task(self.simulator.start())

            logger.info("Simulator started via web interface")
            return web.json_response({"success": True})

        except Exception as e:
            logger.error(f"Error starting simulator: {e}")
            return web.json_response({"success": False, "error": str(e)})
    
    async def stop_simulator_handler(self, request):
        """Stop the simulator"""
        try:
            if not self.simulator or not self.running:
                return web.json_response({"success": False, "error": "Simulator not running"})

            self.running = False
            await self.simulator.stop()
            self.simulator = None

            logger.info("Simulator stopped via web interface")
            return web.json_response({"success": True})

        except Exception as e:
            logger.error(f"Error stopping simulator: {e}")
            return web.json_response({"success": False, "error": str(e)})

    async def add_lot_handler(self, request):
        """Add a new lot to the simulator"""
        try:
            if not self.simulator or not self.running:
                return web.json_response({"success": False, "error": "Simulator not running"})

            # Parse request data
            data = await request.json()

            # Extract lot parameters with defaults
            customer = data.get("customer", "Test Customer")
            quantity = int(data.get("quantity", 100))
            location = data.get("location", "Italy")
            priority = data.get("priority", "normal")

            # Validate location
            valid_locations = ["Italy", "Brazil", "Vietnam"]
            if location not in valid_locations:
                return web.json_response({
                    "success": False,
                    "error": f"Invalid location. Must be one of: {valid_locations}"
                })

            # Validate quantity
            if quantity <= 0 or quantity > 1000:
                return web.json_response({
                    "success": False,
                    "error": "Quantity must be between 1 and 1000"
                })

            # Create lot data
            from datetime import datetime
            import random

            lot_data = {
                "codice_lotto": f"WEB-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                "cliente": customer,
                "quantita": quantity,
                "location": location,
                "priority": priority,
                "timestamp": datetime.now().isoformat()
            }

            # Add lot to simulator
            await self.simulator.add_lot(lot_data)

            logger.info(f"Lot {lot_data['codice_lotto']} added via web interface")
            return web.json_response({
                "success": True,
                "lot_code": lot_data["codice_lotto"],
                "message": f"Lot {lot_data['codice_lotto']} added successfully"
            })

        except ValueError as e:
            return web.json_response({"success": False, "error": f"Invalid data: {e}"})
        except Exception as e:
            logger.error(f"Error adding lot: {e}")
            return web.json_response({"success": False, "error": str(e)})

    async def start_processing_handler(self, request):
        """Manually trigger processing of queued lots"""
        try:
            if not self.simulator or not self.running:
                return web.json_response({"success": False, "error": "Simulator not running"})

            # Get current status to see queued lots
            status = self.simulator.production_coordinator.get_status()
            queued_lots = status.get("queues", {}).get("queued", {}).get("size", 0)
            
            if queued_lots == 0:
                return web.json_response({"success": False, "error": "No lots in queue to process"})

            # Force a single iteration of queue processing
            await self.simulator.production_coordinator._process_single_queue_iteration()
            
            logger.info("Manual lot processing triggered via web interface")
            return web.json_response({
                "success": True,
                "message": f"Processing started for {queued_lots} queued lot(s)"
            })

        except Exception as e:
            logger.error(f"Error starting lot processing: {e}")
            return web.json_response({"success": False, "error": str(e)})

    async def machine_maintenance_handler(self, request):
        """Handle machine maintenance control"""
        try:
            if not self.simulator or not self.running:
                return web.json_response({"success": False, "error": "Simulator not running"})

            data = await request.json()
            machine_id = data.get("machine_id")
            in_maintenance = data.get("in_maintenance", False)
            reason = data.get("reason", "Manual maintenance")

            if not machine_id:
                return web.json_response({"success": False, "error": "machine_id is required"})

            success = self.simulator.production_coordinator.set_machine_maintenance(
                machine_id, in_maintenance, reason
            )

            if success:
                action = "entered" if in_maintenance else "exited"
                logger.info(f"Machine {machine_id} {action} maintenance via web interface")
                return web.json_response({
                    "success": True,
                    "message": f"Machine {machine_id} {action} maintenance successfully"
                })
            else:
                return web.json_response({"success": False, "error": f"Machine {machine_id} not found"})

        except Exception as e:
            logger.error(f"Error controlling machine maintenance: {e}")
            return web.json_response({"success": False, "error": str(e)})

    async def machines_handler(self, request):
        """Get detailed machine information"""
        try:
            if not self.simulator or not self.running:
                return web.json_response({"success": False, "error": "Simulator not running"})

            machines = self.simulator.production_coordinator.get_all_machines()
            return web.json_response({"success": True, "machines": machines})

        except Exception as e:
            logger.error(f"Error getting machine information: {e}")
            return web.json_response({"success": False, "error": str(e)})

    async def status_handler(self, request):
        """Get current status"""
        stats = monitor.get_current_stats()
        stats["simulator_running"] = self.running
        return web.json_response(stats)
    
    async def broadcast_stats(self):
        """Broadcast statistics to all connected WebSocket clients"""
        while True:
            try:
                if self.websockets:
                    stats = monitor.get_current_stats()
                    stats["simulator_running"] = self.running
                    message = json.dumps(stats)
                    
                    # Send to all connected clients
                    disconnected = set()
                    for ws in self.websockets:
                        try:
                            await ws.send_str(message)
                        except Exception:
                            disconnected.add(ws)
                    
                    # Remove disconnected clients
                    self.websockets -= disconnected
                
                await asyncio.sleep(1)  # Broadcast every second
                
            except Exception as e:
                logger.error(f"Error broadcasting stats: {e}")
                await asyncio.sleep(1)
    
    async def start_server(self):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        # Start broadcasting task
        self.broadcast_task = asyncio.create_task(self.broadcast_stats())
        
        print(f"🌐 Web interface started at http://{self.host}:{self.port}")
        print("Open this URL in your browser to access the control panel")
        
        return runner
    
    async def stop_server(self, runner):
        """Stop the web server"""
        if self.broadcast_task:
            self.broadcast_task.cancel()
        
        if self.simulator and self.running:
            await self.stop_simulator_handler(None)
        
        await runner.cleanup()

async def main():
    """Main web interface entry point"""
    interface = WebInterface()
    
    try:
        runner = await interface.start_server()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        print("\n🛑 Shutting down web interface...")
        await interface.stop_server(runner)

if __name__ == "__main__":
    asyncio.run(main())
