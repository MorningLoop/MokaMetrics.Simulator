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

try:
    from .monitoring import monitor
except ImportError:
    from monitoring import monitor

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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* Modern CSS Reset and Base Styles */
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
            min-height: 100vh;
            color: #333;
            overflow-x: hidden;
            transition: all 0.3s ease;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.1);
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }

        .container:hover {
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
        }

        /* Enhanced Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 24px;
            border-radius: 20px;
            margin-bottom: 24px;
            box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255, 255, 255, 0.1) 0%, transparent 100%);
            pointer-events: none;
        }
        .header::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="75" cy="75" r="1" fill="rgba(255,255,255,0.1)"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.1;
        }
        .header h1 { margin: 0; font-size: 2.2em; font-weight: 400; position: relative; z-index: 1; letter-spacing: -0.5px; }
        .header p { margin: 8px 0 0 0; opacity: 0.9; position: relative; z-index: 1; font-size: 1em; }

        /* Enhanced Controls */
        .controls {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%);
            backdrop-filter: blur(10px);
            padding: 24px;
            border-radius: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.4);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .controls::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255, 255, 255, 0.1) 0%, transparent 100%);
            pointer-events: none;
        }

        .controls:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.3);
        }

        .controls h3 {
            margin-top: 0;
            color: #1e293b;
            font-size: 1.3em;
            font-weight: 700;
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
            letter-spacing: -0.3px;
        }

        /* Enhanced Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }

        /* Enhanced Cards */
        .stat-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%);
            backdrop-filter: blur(10px);
            padding: 24px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.4);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            height: fit-content;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255, 255, 255, 0.1) 0%, transparent 100%);
            pointer-events: none;
        }

        .stat-card:hover {
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.3);
        }

        .stat-card h3 {
            margin-top: 0;
            color: #1e293b;
            font-size: 1.3em;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
            position: relative;
            z-index: 1;
            letter-spacing: -0.3px;
        }

        /* Enhanced Buttons */
        .btn {
            padding: 16px 28px;
            margin: 8px;
            border: none;
            border-radius: 16px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-transform: uppercase;
            letter-spacing: 0.3px;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }

        .btn:hover::before {
            left: 100%;
        }
        .btn::before {
            content: '';
            position: absolute;
            top: 0; left: -100%; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        .btn:hover::before { left: 100%; }

        .btn:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }

        .btn:active {
            transform: translateY(-1px) scale(0.98);
            transition: all 0.1s ease;
        }

        .btn-start {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }
        .btn-start:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
        }

        .btn-stop {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
        }
        .btn-stop:hover {
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            box-shadow: 0 8px 25px rgba(239, 68, 68, 0.4);
        }

        .btn-process {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        }
        .btn-process:hover {
            background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
        }
        .btn:disabled {
            background: #bdc3c7; cursor: not-allowed;
            transform: none; box-shadow: none;
        }

        /* Enhanced Status */
        .status {
            padding: 10px; border-radius: 6px; margin: 10px 0;
            font-weight: 500; border-left: 3px solid; font-size: 14px;
        }
        .status.running {
            background: linear-gradient(135deg, #d5f4e6 0%, #a8e6cf 100%);
            color: #27ae60; border-left-color: #27ae60;
        }
        .status.stopped {
            background: linear-gradient(135deg, #fadbd8 0%, #f5b7b1 100%);
            color: #e74c3c; border-left-color: #e74c3c;
        }

        /* Enhanced Tables */
        table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
        th, td { padding: 6px 4px; text-align: left; border-bottom: 1px solid #eee; }
        th {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            font-weight: 600; color: #495057; font-size: 12px;
        }
        tr:hover { background: rgba(0,0,0,0.02); }

        /* Enhanced Metrics */
        .metric {
            font-size: 1.8em; font-weight: 700; color: #2c3e50;
            background: linear-gradient(135deg, #3498db, #2980b9);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .metric-label { font-size: 12px; color: #7f8c8d; font-weight: 500; }

        /* Enhanced Connection Status */
        .connection-status {
            position: fixed; top: 20px; right: 20px;
            padding: 8px 16px; border-radius: 20px;
            font-weight: 500; font-size: 14px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            z-index: 1000;
        }
        .connected {
            background: linear-gradient(135deg, #d5f4e6 0%, #a8e6cf 100%);
            color: #27ae60;
        }
        .disconnected {
            background: linear-gradient(135deg, #fadbd8 0%, #f5b7b1 100%);
            color: #e74c3c;
        }

        /* Form Enhancements */
        input, select {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid rgba(226, 232, 240, 0.8);
            border-radius: 16px;
            font-size: 15px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-weight: 500;
            color: #334155;
            letter-spacing: -0.1px;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1), 0 4px 12px rgba(102, 126, 234, 0.15);
            background: rgba(255, 255, 255, 1);
            transform: translateY(-1px);
        }

        input:hover, select:hover {
            border-color: rgba(102, 126, 234, 0.5);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        label {
            display: block; margin-bottom: 3px; font-weight: 500;
            color: #495057; font-size: 12px;
        }

        /* Pet Widget Styles */
        .pet-widget {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border: 2px solid #fdcb6e;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .pet-container {
            font-size: 2.5em;
            margin: 8px 0;
            position: relative;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .pet-bean {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            animation: petIdle 2s ease-in-out infinite;
            cursor: pointer;
            font-size: 2em;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
            position: relative;
        }

        .pet-bean:hover {
            transform: scale(1.1);
            filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.3));
        }

        .pet-bean.happy {
            animation: petHappy 0.6s ease-in-out;
        }
        @keyframes petIdle {
            0%, 100% {
                transform: translateY(0px) rotate(0deg) scale(1);
                filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
            }
            50% {
                transform: translateY(-8px) rotate(3deg) scale(1.02);
                filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.3));
            }
        }

        @keyframes petHappy {
            0%, 100% {
                transform: scale(1) rotate(0deg);
                filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2)) hue-rotate(0deg);
            }
            25% {
                transform: scale(1.2) rotate(-10deg);
                filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.3)) hue-rotate(60deg);
            }
            75% {
                transform: scale(1.2) rotate(10deg);
                filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.3)) hue-rotate(-60deg);
            }
        }

        /* Add pulse animation for connection status */
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
        }

        .pulse { animation: pulse 2s ease-in-out infinite; }
        .pet-progress {
            background: #e9ecef;
            border-radius: 10px;
            height: 6px;
            margin: 8px 0;
            overflow: hidden;
        }
        .pet-progress-bar {
            background: linear-gradient(90deg, #fdcb6e, #e17055);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        .pet-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 11px;
            margin-top: 8px;
        }


        /* Toggle Switch Styles */
        .toggle-container {
            margin: 15px 0;
        }
        .toggle-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }

        .toggle-switch {
            position: relative;
            display: inline-block;
        }

        .toggle-input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .toggle-slider {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 26px;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
            border-radius: 26px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .toggle-button {
            position: absolute;
            top: 2px;
            left: 2px;
            width: 20px;
            height: 20px;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border-radius: 50%;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 0, 0, 0.1);
        }

        .toggle-input:checked + .toggle-slider {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1), 0 0 15px rgba(16, 185, 129, 0.3);
        }

        .toggle-input:checked + .toggle-slider .toggle-button {
            transform: translateX(24px);
            background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
            box-shadow: 0 2px 12px rgba(16, 185, 129, 0.4);
        }

        .toggle-slider:hover {
            transform: scale(1.05);
        }

        .toggle-input:checked + .toggle-slider:hover {
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1), 0 0 20px rgba(16, 185, 129, 0.4);
        }
        .slider {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
            transition: background 0.3s;
        }
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #74b9ff;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            transition: all 0.2s;
        }
        .slider::-webkit-slider-thumb:hover {
            background: #0984e3;
            transform: scale(1.1);
        }
        .slider::-moz-range-thumb {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #74b9ff;
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }



        /* Retro Terminal Mode Styles */
        .retro-mode {
            transition: all 0.5s ease;
        }
        .retro-mode.active {
            background: #000 !important;
            color: #00ff00 !important;
            font-family: 'Courier New', monospace !important;
        }
        .retro-mode.active .stat-card,
        .retro-mode.active .controls {
            background: #001100 !important;
            border: 1px solid #00ff00 !important;
            color: #00ff00 !important;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.3) !important;
        }
        .retro-mode.active .header {
            background: #001100 !important;
            border: 1px solid #00ff00 !important;
            color: #00ff00 !important;
        }
        .retro-mode.active .btn {
            background: #003300 !important;
            color: #00ff00 !important;
            border: 1px solid #00ff00 !important;
        }
        .retro-mode.active .btn:hover {
            background: #00ff00 !important;
            color: #000 !important;
        }
        .retro-mode.active input,
        .retro-mode.active select {
            background: #001100 !important;
            color: #00ff00 !important;
            border: 1px solid #00ff00 !important;
        }
        .retro-mode.active table th {
            background: #003300 !important;
            color: #00ff00 !important;
        }

        /* Responsive Design */
        @media (max-width: 1200px) {
            .stats-grid { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
        }
        @media (max-width: 768px) {
            body { padding: 8px; }
            .header { padding: 16px; margin-bottom: 16px; }
            .header h1 { font-size: 1.8em; }
            .stats-grid { grid-template-columns: 1fr 1fr; gap: 12px; }
            .controls { padding: 16px; margin-bottom: 16px; }
            .stat-card { padding: 16px; }
            .btn { padding: 12px 20px; font-size: 14px; }
        }
        @media (max-width: 480px) {
            .stats-grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 1.6em; }
            .controls h3, .stat-card h3 { font-size: 1.1em; }
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">Connecting...</div>

    <div class="container" id="mainContainer">
        <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h1><i class="fas fa-industry"></i> MokaMetrics Simulator Control Panel</h1>
                    <p><i class="fas fa-clock"></i> Ultra Fast Testing Mode - 40-second total production cycles</p>
                    <p><i class="fas fa-server"></i> Kafka Broker: 165.227.168.240:29093</p>
                </div>
                <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 12px;">
                    <div class="toggle-container" style="margin: 0; background: rgba(255, 255, 255, 0.1); padding: 12px 16px; border-radius: 12px; backdrop-filter: blur(10px);">
                        <div class="toggle-label" style="margin-bottom: 0;">
                            <span style="color: white; font-size: 14px; font-weight: 600;"><i class="fas fa-terminal"></i> Retro Terminal</span>
                            <div class="toggle-switch" id="retroToggle">
                                <input type="checkbox" id="retroCheckbox" class="toggle-input">
                                <label for="retroCheckbox" class="toggle-slider">
                                    <span class="toggle-button"></span>
                                </label>
                            </div>
                        </div>
                    </div>
                    <div style="font-size: 14px; opacity: 0.8;">
                        <div id="currentTime">--</div>
                        <div>System Ready</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <h3><i class="fas fa-play-circle"></i> Simulator Control</h3>
            <div style="display: grid; grid-template-columns: 1fr auto; gap: 15px; align-items: center; margin-bottom: 15px;">
                <div>
                    <div class="status" id="simulatorStatus">Status: Unknown</div>
                    <div style="margin-top: 8px; font-size: 12px; color: #666;">
                        <div><i class="fas fa-microchip"></i> Health: <span id="healthStatus">Checking...</span></div>
                        <div><i class="fas fa-database"></i> Kafka: <span id="kafkaStatus">Checking...</span></div>
                    </div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5em; margin-bottom: 3px;" id="statusIcon">⚪</div>
                    <div style="font-size: 11px; color: #666;" id="statusText">Idle</div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="btn btn-start" id="startBtn" onclick="startSimulator()">
                    <i class="fas fa-play"></i> Start Simulator
                </button>
                <button class="btn btn-stop" id="stopBtn" onclick="stopSimulator()" disabled>
                    <i class="fas fa-stop"></i> Stop Simulator
                </button>
                <button class="btn btn-process" id="startProcessingBtn" onclick="startProcessing()" disabled>
                    <i class="fas fa-rocket"></i> Start Processing Queued Lots
                </button>
            </div>
        </div>



        <div class="controls">
            <h3><i class="fas fa-plus-circle"></i> Add New Lot</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 15px;">
                <div>
                    <label for="customer"><i class="fas fa-user"></i> Customer:</label>
                    <input type="text" id="customer" placeholder="Enter customer name" value="Test Customer">
                    <div style="font-size: 10px; color: #666; margin-top: 1px;">Required</div>
                </div>
                <div>
                    <label for="quantity"><i class="fas fa-boxes"></i> Quantity:</label>
                    <input type="number" id="quantity" placeholder="100" value="100" min="1" max="1000">
                    <div style="font-size: 10px; color: #666; margin-top: 1px;">1-1000</div>
                </div>
                <div>
                    <label for="location"><i class="fas fa-map-marker-alt"></i> Location:</label>
                    <select id="location">
                        <option value="Italy">🇮🇹 Italy</option>
                        <option value="Brazil">🇧🇷 Brazil</option>
                        <option value="Vietnam">🇻🇳 Vietnam</option>
                    </select>
                    <div style="font-size: 10px; color: #666; margin-top: 1px;">Facility</div>
                </div>
                <div>
                    <label for="priority"><i class="fas fa-flag"></i> Priority:</label>
                    <select id="priority">
                        <option value="normal">🟢 Normal</option>
                        <option value="high">🟡 High</option>
                        <option value="urgent">🔴 Urgent</option>
                    </select>
                    <div style="font-size: 10px; color: #666; margin-top: 1px;">Priority</div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <button class="btn btn-start" id="addLotBtn" onclick="addLot()" disabled>
                    <i class="fas fa-plus"></i> Add Lot
                </button>
                <button class="btn" onclick="generateRandomLot()" style="background: #3498db; color: white;">
                    <i class="fas fa-random"></i> Generate Random
                </button>
                <button class="btn" onclick="clearForm()" style="background: #95a5a6; color: white;">
                    <i class="fas fa-eraser"></i> Clear
                </button>
            </div>
            <div id="addLotStatus" style="margin-top: 15px;"></div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card pet-widget">
                <h3><i class="fas fa-seedling"></i> Simulator Pet</h3>
                <div class="pet-container">
                    <div class="pet-bean" id="petBean" onclick="petClick()">🌱</div>
                </div>
                <div class="pet-progress">
                    <div class="pet-progress-bar" id="petProgressBar" style="width: 0%"></div>
                </div>
                <div style="font-size: 12px; font-weight: 600; margin-bottom: 5px;" id="petStage">Seed Stage</div>
                <div class="pet-stats">
                    <div><strong id="petMessages">0</strong><br><span style="color: #666;">Messages</span></div>
                    <div><strong id="petGrowth">0%</strong><br><span style="color: #666;">Growth</span></div>
                </div>
            </div>

            <div class="stat-card">
                <h3><i class="fas fa-chart-bar"></i> System Statistics</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; text-align: center;">
                    <div>
                        <div class="metric" id="uptime">--</div>
                        <div class="metric-label">Uptime</div>
                    </div>
                    <div>
                        <div class="metric" id="totalLots">0</div>
                        <div class="metric-label">Completed Lots</div>
                    </div>
                    <div>
                        <div class="metric" id="messagesPerSec">0</div>
                        <div class="metric-label">Messages/Sec</div>
                    </div>
                </div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 3px;">Performance</div>
                    <div style="display: flex; justify-content: space-between; font-size: 11px;">
                        <span>CPU: <span id="cpuUsage">--</span>%</span>
                        <span>Mem: <span id="memUsage">--</span>%</span>
                        <span>Queue: <span id="queueSize">--</span></span>
                    </div>
                </div>
            </div>

            <div class="stat-card">
                <h3><i class="fas fa-boxes"></i> Active Lots</h3>
                <div id="activeLots">No active lots</div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #666;">
                        <span>Queue: <span id="queuedLots">0</span></span>
                        <span>Active: <span id="processingLots">0</span></span>
                        <span>Done: <span id="completedLots">0</span></span>
                    </div>
                </div>
            </div>

            <div class="stat-card">
                <h3><i class="fas fa-cogs"></i> Machine Utilization</h3>
                <div id="machineStats">No machine data</div>
                <div style="margin-top: 10px;">
                    <canvas id="utilizationChart" width="300" height="120"></canvas>
                </div>
            </div>

            <div class="stat-card">
                <h3><i class="fas fa-chart-line"></i> Production Trends</h3>
                <div style="margin-bottom: 8px;">
                    <canvas id="productionChart" width="300" height="140"></canvas>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #666;">
                    <span>Peak: <span id="peakRate">0</span></span>
                    <span>Avg: <span id="avgRate">0</span></span>
                    <span>Now: <span id="currentRate">0</span></span>
                </div>
            </div>
            
            <div class="stat-card">
                <h3><i class="fas fa-tools"></i> Machine Maintenance</h3>
                <div id="maintenanceControls">
                    <div style="margin-bottom: 10px;">
                        <label for="machineSelect"><i class="fas fa-robot"></i> Machine:</label>
                        <select id="machineSelect">
                            <option value="">Select machine...</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <label for="maintenanceReason"><i class="fas fa-comment"></i> Reason:</label>
                        <input type="text" id="maintenanceReason" placeholder="Maintenance reason...">
                    </div>
                    <div style="display: flex; gap: 6px; margin-bottom: 10px;">
                        <button class="btn btn-start" id="startMaintenanceBtn" onclick="setMaintenance(true)" disabled style="flex: 1;">
                            <i class="fas fa-wrench"></i> Start
                        </button>
                        <button class="btn btn-stop" id="stopMaintenanceBtn" onclick="setMaintenance(false)" disabled style="flex: 1;">
                            <i class="fas fa-check"></i> Done
                        </button>
                    </div>
                    <div id="maintenanceStatus"></div>
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                        <div style="font-size: 12px; color: #666; margin-bottom: 3px;">Quick Actions</div>
                        <div style="display: flex; gap: 3px;">
                            <button class="btn" onclick="setMaintenanceReason('Scheduled')" style="background: #f39c12; color: white; font-size: 10px; padding: 4px 6px;">
                                Scheduled
                            </button>
                            <button class="btn" onclick="setMaintenanceReason('Emergency')" style="background: #e74c3c; color: white; font-size: 10px; padding: 4px 6px;">
                                Emergency
                            </button>
                            <button class="btn" onclick="setMaintenanceReason('Preventive')" style="background: #27ae60; color: white; font-size: 10px; padding: 4px 6px;">
                                Preventive
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="stat-card">
                <h3><i class="fas fa-stream"></i> Kafka Topics</h3>
                <div id="topicStats">No topic data</div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #666;">
                        <span>Total: <span id="totalMessages">0</span></span>
                        <span>Errors: <span id="messageErrors">0</span></span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let simulatorRunning = false;
        let productionChart = null;
        let utilizationChart = null;
        let productionData = [];
        let utilizationData = [];

        // Pet system variables
        let petData = {
            stage: 0, // 0=Seed, 1=Sprout, 2=Small Bean, 3=Medium Bean, 4=Large Bean, 5=Golden Bean
            totalMessages: 0,
            growth: 0,
            lastMessageTime: 0
        };

        // Visual effects variables
        let retroLevel = 0;

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            connectWebSocket();
            updateCurrentTime();
            setInterval(updateCurrentTime, 1000);

            // Form validation
            document.getElementById('customer').addEventListener('input', validateForm);
            document.getElementById('quantity').addEventListener('input', validateForm);
            validateForm();

            // Check system health
            checkSystemHealth();
            setInterval(checkSystemHealth, 30000); // Check every 30 seconds

            // Initialize visual effects
            initializeVisualEffects();
            loadPetData();
        });

        function updateCurrentTime() {
            const now = new Date();
            document.getElementById('currentTime').textContent = now.toLocaleString();
        }

        function initializeCharts() {
            // Production Chart
            const productionCtx = document.getElementById('productionChart');
            if (productionCtx) {
                productionChart = new Chart(productionCtx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Messages/Min',
                            data: [],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true },
                            x: { display: false }
                        },
                        plugins: { legend: { display: false } }
                    }
                });
            }

            // Utilization Chart
            const utilizationCtx = document.getElementById('utilizationChart');
            if (utilizationCtx) {
                utilizationChart = new Chart(utilizationCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Working', 'Idle', 'Maintenance'],
                        datasets: [{
                            data: [0, 0, 0],
                            backgroundColor: ['#27ae60', '#f39c12', '#e74c3c']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { font: { size: 10 } }
                            }
                        }
                    }
                });
            }
        }

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = function() {
                document.getElementById('connectionStatus').textContent = 'Connected';
                document.getElementById('connectionStatus').className = 'connection-status connected';
                updateSystemStatus('🟢', 'Connected');
                console.log('WebSocket connected');
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDisplay(data);
            };

            ws.onclose = function() {
                document.getElementById('connectionStatus').textContent = 'Disconnected';
                document.getElementById('connectionStatus').className = 'connection-status disconnected';
                updateSystemStatus('🔴', 'Disconnected');
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateSystemStatus('🟡', 'Error');
            };
        }
        
        function updateSystemStatus(icon, text) {
            document.getElementById('statusIcon').textContent = icon;
            document.getElementById('statusText').textContent = text;
        }

        function validateForm() {
            const customer = document.getElementById('customer').value.trim();
            const quantity = parseInt(document.getElementById('quantity').value);
            const isValid = customer.length > 0 && quantity > 0 && quantity <= 1000;

            document.getElementById('addLotBtn').disabled = !isValid || !simulatorRunning;

            // Visual feedback
            document.getElementById('customer').style.borderColor = customer.length > 0 ? '#27ae60' : '#e74c3c';
            document.getElementById('quantity').style.borderColor = (quantity > 0 && quantity <= 1000) ? '#27ae60' : '#e74c3c';
        }

        function checkSystemHealth() {
            // Simulate health checks
            document.getElementById('healthStatus').textContent = '✅ Healthy';
            document.getElementById('kafkaStatus').textContent = '✅ Connected';

            // Simulate performance metrics
            document.getElementById('cpuUsage').textContent = Math.floor(Math.random() * 30 + 10);
            document.getElementById('memUsage').textContent = Math.floor(Math.random() * 40 + 20);
            document.getElementById('queueSize').textContent = Math.floor(Math.random() * 10);
        }

        function updateDisplay(stats) {
            // Update system stats
            document.getElementById('uptime').textContent = stats.uptime_formatted || '--';
            document.getElementById('totalLots').textContent = stats.total_lots_completed || 0;
            document.getElementById('messagesPerSec').textContent = stats.messages_per_second || 0;

            // Update production chart
            if (productionChart && stats.messages_per_minute !== undefined) {
                const now = new Date().toLocaleTimeString();
                productionData.push({
                    time: now,
                    value: stats.messages_per_minute
                });

                // Keep only last 20 data points
                if (productionData.length > 20) {
                    productionData.shift();
                }

                productionChart.data.labels = productionData.map(d => d.time);
                productionChart.data.datasets[0].data = productionData.map(d => d.value);
                productionChart.update('none');

                // Update production metrics
                const rates = productionData.map(d => d.value);
                document.getElementById('peakRate').textContent = Math.max(...rates, 0);
                document.getElementById('avgRate').textContent = Math.round(rates.reduce((a, b) => a + b, 0) / rates.length) || 0;
                document.getElementById('currentRate').textContent = stats.messages_per_minute || 0;
            }
            
            // Update active lots with enhanced display
            const activeLots = stats.active_lots || [];

            // Update lot counters
            const queuedLots = activeLots.filter(lot => lot.current_stage === 'queued').length;
            const processingLots = activeLots.filter(lot => lot.current_stage !== 'queued' && lot.current_stage !== 'completed').length;
            const completedLots = stats.total_lots_completed || 0;

            document.getElementById('queuedLots').textContent = queuedLots;
            document.getElementById('processingLots').textContent = processingLots;
            document.getElementById('completedLots').textContent = completedLots;

            const lotsHtml = activeLots.length > 0 ?
                `<div style="max-height: 120px; overflow-y: auto;">
                    <table style="font-size: 11px;">
                        <tr><th>Lot</th><th>Customer</th><th>Stage</th><th>Location</th><th>%</th></tr>` +
                activeLots.slice(0, 6).map(lot => {
                    const progress = getStageProgress(lot.current_stage);
                    const stageIcon = getStageIcon(lot.current_stage);
                    return `<tr>
                        <td><strong>${lot.lot_code}</strong></td>
                        <td>${lot.customer}</td>
                        <td>${stageIcon} ${lot.current_stage}</td>
                        <td>${getFlagIcon(lot.location)} ${lot.location}</td>
                        <td>
                            <div style="background: #eee; border-radius: 8px; height: 6px; width: 40px;">
                                <div style="background: #3498db; height: 6px; border-radius: 8px; width: ${progress}%;"></div>
                            </div>
                        </td>
                    </tr>`;
                }).join('') + '</table></div>' :
                '<div style="text-align: center; padding: 20px; color: #666;"><i class="fas fa-inbox" style="font-size: 2em; margin-bottom: 10px;"></i><br>No active lots</div>';
            document.getElementById('activeLots').innerHTML = lotsHtml;
            
            // Update machine stats with enhanced display
            const machines = stats.machine_utilization || [];

            // Calculate machine status counts
            let workingCount = 0, idleCount = 0, maintenanceCount = 0;
            machines.forEach(machine => {
                if (machine.is_busy) workingCount++;
                else if (machine.maintenance_mode) maintenanceCount++;
                else idleCount++;
            });

            // Update utilization chart
            if (utilizationChart) {
                utilizationChart.data.datasets[0].data = [workingCount, idleCount, maintenanceCount];
                utilizationChart.update('none');
            }

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
                `<div style="max-height: 120px; overflow-y: auto;">
                    <table style="font-size: 11px;">
                        <tr><th>Machine</th><th>Type</th><th>Status</th><th>%</th></tr>` +
                relevantMachines.map(machine => {
                    const statusIcon = machine.is_busy ? '🟢' : machine.maintenance_mode ? '🔧' : '⚪';
                    const statusText = machine.is_busy ? 'Working' : machine.maintenance_mode ? 'Maintenance' : 'Idle';
                    const utilization = machine.utilization_percentage.toFixed(1);
                    return `<tr>
                        <td><strong>${machine.machine_id}</strong></td>
                        <td>${machine.machine_type}</td>
                        <td>${statusIcon} ${statusText}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 3px;">
                                <div style="background: #eee; border-radius: 8px; height: 4px; width: 30px;">
                                    <div style="background: ${machine.is_busy ? '#27ae60' : '#95a5a6'}; height: 4px; border-radius: 8px; width: ${utilization}%;"></div>
                                </div>
                                <span style="font-size: 10px;">${utilization}%</span>
                            </div>
                        </td>
                    </tr>`;
                }).join('') + '</table></div>' :
                '<div style="text-align: center; padding: 20px; color: #666;"><i class="fas fa-robot" style="font-size: 2em; margin-bottom: 10px;"></i><br>No machine data</div>';
            document.getElementById('machineStats').innerHTML = machinesHtml;
            
            // Update topic stats with enhanced display
            const topics = stats.topic_stats || {};
            let totalMessages = 0, totalErrors = 0;

            const topicsHtml = Object.keys(topics).length > 0 ?
                `<div style="max-height: 100px; overflow-y: auto;">
                    <table style="font-size: 11px;">
                        <tr><th>Topic</th><th>Total</th><th>/min</th><th>●</th></tr>` +
                Object.entries(topics).map(([topic, topicStats]) => {
                    totalMessages += topicStats.total_sent || 0;
                    totalErrors += topicStats.errors || 0;
                    const shortTopic = topic.replace('mokametrics.', '');
                    const statusIcon = topicStats.per_minute > 0 ? '🟢' : '⚪';
                    return `<tr>
                        <td><strong>${shortTopic}</strong></td>
                        <td>${topicStats.total_sent || 0}</td>
                        <td>${topicStats.per_minute || 0}</td>
                        <td>${statusIcon}</td>
                    </tr>`;
                }).join('') + '</table></div>' :
                '<div style="text-align: center; padding: 20px; color: #666;"><i class="fas fa-stream" style="font-size: 2em; margin-bottom: 10px;"></i><br>No topic data</div>';
            document.getElementById('topicStats').innerHTML = topicsHtml;

            // Update totals
            document.getElementById('totalMessages').textContent = totalMessages;
            document.getElementById('messageErrors').textContent = totalErrors;

            // Update pet with message count
            updatePetFromMessages(totalMessages);

            // Update simulator status
            if (stats.simulator_running !== undefined) {
                simulatorRunning = stats.simulator_running;
                updateSimulatorButtons();

                const statusElement = document.getElementById('simulatorStatus');
                if (simulatorRunning) {
                    statusElement.textContent = 'Status: Running';
                    statusElement.className = 'status running';
                    updateSystemStatus('🟢', 'Running');
                } else {
                    statusElement.textContent = 'Status: Stopped';
                    statusElement.className = 'status stopped';
                    updateSystemStatus('🔴', 'Stopped');
                }
            }
        }

        // Helper functions
        function getStageProgress(stage) {
            const stages = { 'queued': 0, 'cnc': 25, 'lathe': 50, 'assembly': 75, 'testing': 90, 'completed': 100 };
            return stages[stage] || 0;
        }

        function getStageIcon(stage) {
            const icons = {
                'queued': '⏳', 'cnc': '🔧', 'lathe': '⚙️',
                'assembly': '🔩', 'testing': '🧪', 'completed': '✅'
            };
            return icons[stage] || '❓';
        }

        function getFlagIcon(location) {
            const flags = { 'Italy': '🇮🇹', 'Brazil': '🇧🇷', 'Vietnam': '🇻🇳' };
            return flags[location] || '🏭';
        }

        // Pet System Functions
        function initializePetSystem() {
            updatePetDisplay();
        }

        function updatePetFromMessages(messageCount) {
            if (messageCount > petData.totalMessages) {
                const newMessages = messageCount - petData.totalMessages;
                petData.totalMessages = messageCount;
                petData.growth = Math.min(100, petData.growth + newMessages * 0.5);

                // Trigger happy animation
                const petBean = document.getElementById('petBean');
                petBean.classList.add('happy');
                setTimeout(() => petBean.classList.remove('happy'), 600);

                // Check for stage evolution
                const newStage = Math.floor(petData.growth / 20);
                if (newStage > petData.stage && newStage <= 5) {
                    petData.stage = newStage;
                    showPetEvolution();
                }

                updatePetDisplay();
                savePetData();
            }
        }

        function updatePetDisplay() {
            const stages = ['🌱', '🌿', '☕', '☕', '☕', '✨☕✨'];
            const stageNames = ['Seed', 'Sprout', 'Small Bean', 'Medium Bean', 'Large Bean', 'Golden Bean'];

            document.getElementById('petBean').textContent = stages[petData.stage] || '🌱';
            document.getElementById('petStage').textContent = `${stageNames[petData.stage] || 'Seed'} Stage`;
            document.getElementById('petMessages').textContent = petData.totalMessages;
            document.getElementById('petGrowth').textContent = `${Math.floor(petData.growth)}%`;
            document.getElementById('petProgressBar').style.width = `${petData.growth}%`;
        }

        function showPetEvolution() {
            const petBean = document.getElementById('petBean');
            petBean.style.transform = 'scale(1.5)';
            petBean.style.filter = 'brightness(1.5)';

            setTimeout(() => {
                petBean.style.transform = 'scale(1)';
                petBean.style.filter = 'brightness(1)';
            }, 1000);
        }

        function petClick() {
            const petBean = document.getElementById('petBean');
            petBean.classList.add('happy');
            setTimeout(() => petBean.classList.remove('happy'), 600);
        }

        function savePetData() {
            localStorage.setItem('mokaPetData', JSON.stringify(petData));
        }

        function loadPetData() {
            const saved = localStorage.getItem('mokaPetData');
            if (saved) {
                petData = { ...petData, ...JSON.parse(saved) };
            }
            updatePetDisplay();
        }

        // Visual Effects Functions
        function initializeVisualEffects() {
            const retroToggle = document.getElementById('retroCheckbox');

            // Load saved preferences
            const savedRetro = localStorage.getItem('mokaRetroMode');
            const isRetroMode = savedRetro === 'true';

            if (retroToggle) {
                retroToggle.checked = isRetroMode;
            }

            // Add event listeners
            if (retroToggle) {
                retroToggle.addEventListener('change', updateRetroMode);
            }

            // Apply initial states
            updateRetroMode();
        }



        function updateRetroMode() {
            const toggle = document.getElementById('retroCheckbox');
            const container = document.getElementById('mainContainer');

            if (!toggle || !container) return;

            const isRetroMode = toggle.checked;

            if (isRetroMode) {
                container.classList.add('retro-mode', 'active');
                // Add retro terminal effects
                container.style.fontFamily = "'Courier New', monospace";
                container.style.filter = "hue-rotate(120deg) contrast(1.2)";
            } else {
                container.classList.remove('retro-mode', 'active');
                // Remove retro terminal effects
                container.style.fontFamily = "";
                container.style.filter = "";
            }

            localStorage.setItem('mokaRetroMode', isRetroMode.toString());
        }



        // New helper functions
        function generateRandomLot() {
            const customers = ['Acme Coffee Corp', 'Global Espresso Ltd', 'Premium Coffee Systems', 'Elite Brewing Co', 'Artisan Coffee Works'];
            const locations = ['Italy', 'Brazil', 'Vietnam'];
            const priorities = ['normal', 'high', 'urgent'];

            document.getElementById('customer').value = customers[Math.floor(Math.random() * customers.length)];
            document.getElementById('quantity').value = Math.floor(Math.random() * 200) + 50;
            document.getElementById('location').value = locations[Math.floor(Math.random() * locations.length)];
            document.getElementById('priority').value = priorities[Math.floor(Math.random() * priorities.length)];

            validateForm();
            showAddLotStatus('info', '🎲 Random lot data generated');
        }

        function clearForm() {
            document.getElementById('customer').value = '';
            document.getElementById('quantity').value = '100';
            document.getElementById('location').value = 'Italy';
            document.getElementById('priority').value = 'normal';
            document.getElementById('maintenanceReason').value = '';

            validateForm();
            showAddLotStatus('info', '🧹 Form cleared');
        }

        function setMaintenanceReason(reason) {
            document.getElementById('maintenanceReason').value = reason;
        }

        function updateSimulatorButtons() {
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const startProcessingBtn = document.getElementById('startProcessingBtn');
            const addLotBtn = document.getElementById('addLotBtn');

            startBtn.disabled = simulatorRunning;
            stopBtn.disabled = !simulatorRunning;
            startProcessingBtn.disabled = !simulatorRunning;

            // Re-validate form to update add lot button
            validateForm();
        }

        function showAddLotStatus(type, message) {
            const statusDiv = document.getElementById('addLotStatus');
            const colors = {
                'success': '#d5f4e6',
                'error': '#fadbd8',
                'info': '#d6eaf8'
            };

            statusDiv.innerHTML = `
                <div style="padding: 10px; border-radius: 8px; background: ${colors[type] || colors.info}; margin-top: 10px;">
                    ${message}
                </div>
            `;

            // Auto-hide after 5 seconds
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        }

        async function startSimulator() {
            try {
                const response = await fetch('/api/start', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    simulatorRunning = true;
                    updateSimulatorButtons();
                    showAddLotStatus('success', '✅ Simulator started successfully');
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
                    updateSimulatorButtons();
                    showAddLotStatus('info', '⏹️ Simulator stopped');
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
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON received from WebSocket: {msg.data}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.websockets)}")

        return ws

    async def _handle_websocket_message(self, ws, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type", "")

        if message_type == "refresh":
            # Send fresh stats data
            stats = monitor.get_current_stats()
            await ws.send_str(json.dumps(stats))
        else:
            logger.debug(f"Unknown WebSocket message type: {message_type}")
    
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
                    # Get base stats
                    stats = monitor.get_current_stats()
                    stats["simulator_running"] = self.running

                    # Send to all connected clients
                    disconnected = set()
                    for ws in self.websockets:
                        try:
                            await ws.send_str(json.dumps(stats))
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
