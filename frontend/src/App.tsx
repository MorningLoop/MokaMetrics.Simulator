import { useState, useEffect } from "react";
import { Factory, Wifi, WifiOff, Play } from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { SimulatorControls } from "./components/simulator/SimulatorControls";
import { MachineStatusCard, type MachineData } from "./components/simulator/MachineStatusCard";
import { ProductionChart } from "./components/simulator/ProductionChart";
import { CoffeeBeanMascot } from "./components/simulator/CoffeeBeanMascot";
import { RetroEffectsControl } from "./components/simulator/RetroEffectsControl";
import { LotProcessingPanel } from "./components/simulator/LotProcessingPanel";
import { apiService, handleApiCall } from "./services/api";

interface ProductionDataPoint {
    time: string;
    value: number;
}

function App() {
    const { data, connected, error, lastUpdate } = useWebSocket();
    const [retroMode, setRetroMode] = useState(false);
    const [retroIntensity, setRetroIntensity] = useState(0);
    const [machines, setMachines] = useState<MachineData[]>([]);
    const [productionData, setProductionData] = useState<ProductionDataPoint[]>([]);

    // API handlers
    const handleStartSimulator = async () => {
        await handleApiCall(
            () => apiService.startSimulator(),
            () => console.log("Simulator started successfully"),
            (error) => console.error("Failed to start simulator:", error)
        );
    };

    const handleStopSimulator = async () => {
        await handleApiCall(
            () => apiService.stopSimulator(),
            () => console.log("Simulator stopped successfully"),
            (error) => console.error("Failed to stop simulator:", error)
        );
    };

    const handleMachineMaintenance = async (machineId: string) => {
        await handleApiCall(
            () => apiService.machineMaintenance({ machineId, action: "start" }),
            () => console.log(`Maintenance started for machine ${machineId}`),
            (error) => console.error("Failed to start maintenance:", error)
        );
    };

    const handleAddLot = async (lotData: {
        customer: string;
        quantity: number;
        orderDate?: string;
        deadline?: string;
    }) => {
        await handleApiCall(
            () => apiService.addLot(lotData),
            () => console.log("Lot added successfully"),
            (error) => console.error("Failed to add lot:", error)
        );
    };

    const handleStartProcessing = async () => {
        await handleApiCall(
            () => apiService.startProcessing(),
            () => console.log("Processing started successfully"),
            (error) => console.error("Failed to start processing:", error)
        );
    };

    const handleRetroModeChange = (enabled: boolean) => {
        setRetroMode(enabled);
    };

    const handleRetroIntensityChange = (intensity: number) => {
        setRetroIntensity(intensity);
    };

    // Update production chart data when WebSocket data changes
    useEffect(() => {
        if (data?.messages_per_minute !== undefined) {
            const now = new Date();
            const newDataPoint: ProductionDataPoint = {
                time: now.toLocaleTimeString(),
                value: data.messages_per_minute,
            };

            setProductionData((prev) => {
                const updated = [...prev, newDataPoint];
                // Keep only last 20 data points
                return updated.slice(-20);
            });
        }
    }, [data?.messages_per_minute]);

    // Update machine data from WebSocket
    useEffect(() => {
        if (data?.machine_utilization) {
            const realMachines: MachineData[] = data.machine_utilization.map((machine: any) => {
                // Map machine status from backend to our status types
                const getStatus = (
                    is_busy: boolean,
                    machine_type: string,
                    maintenance_mode?: boolean,
                    in_maintenance?: boolean
                ): "running" | "idle" | "maintenance" | "error" => {
                    // Check for maintenance status first
                    if (maintenance_mode || in_maintenance || machine_type.includes("maintenance")) {
                        return "maintenance";
                    }
                    // Check if machine is actively working
                    if (is_busy) return "running";
                    // Default to idle
                    return "idle";
                };

                // Helper function to format machine names from snake_case to Title Case
                const formatMachineName = (machineId: string, machineType: string) => {
                    // Convert machine type to proper title case
                    const typeMap: Record<string, string> = {
                        cnc: "CNC",
                        fresa_cnc: "CNC",
                        tornio: "Lathe",
                        assemblaggio: "Assembly",
                        test: "Testing",
                    };

                    const formattedType =
                        typeMap[machineType] || machineType.charAt(0).toUpperCase() + machineType.slice(1);

                    // Extract machine number/identifier from machine_id (e.g., "cnc_Italy_1" -> "Italy 1")
                    const parts = machineId.split("_");
                    if (parts.length >= 3) {
                        // Format: type_location_number -> "Type Location Number"
                        const location = parts[1];
                        const number = parts[2];
                        return `${formattedType} ${location} ${number}`;
                    } else if (parts.length === 2) {
                        // Format: type_number -> "Type Number"
                        return `${formattedType} ${parts[1]}`;
                    } else {
                        // Fallback: just use the formatted type and ID
                        return `${formattedType} ${machineId}`;
                    }
                };

                // Calculate actual progress based on machine operational status
                const calculateProgress = () => {
                    if (!machine.current_lot) {
                        return 0; // No active lot, no progress
                    }

                    if (machine.maintenance_mode || machine.in_maintenance) {
                        return 0; // Maintenance mode, no production progress
                    }

                    // Convert utilization from decimal to percentage (e.g., 0.36 -> 36%)
                    const utilizationPercent = (machine.utilization_percentage || 0) * 100;

                    if (machine.is_busy) {
                        // For busy machines, use utilization percentage as progress indicator
                        // Ensure it's between 10-95% to show active work
                        return Math.min(95, Math.max(10, utilizationPercent));
                    } else {
                        // Idle with a lot assigned might be between operations
                        return Math.min(5, utilizationPercent);
                    }
                };

                return {
                    id: machine.machine_id,
                    name: formatMachineName(machine.machine_id, machine.machine_type),
                    type: machine.machine_type,
                    status: getStatus(
                        machine.is_busy,
                        machine.machine_type,
                        machine.maintenance_mode,
                        machine.in_maintenance
                    ),
                    currentLot: machine.current_lot || undefined,
                    progress: calculateProgress(),
                    facility: machine.location,
                    throughput: machine.lots_processed,
                    lastUpdate: new Date(),
                };
            });
            // Show only first 8 machines to avoid UI clutter
            setMachines(realMachines.slice(0, 8));
        } else if (machines.length === 0) {
            // Fallback to mock data if no real data available yet
            const mockMachines: MachineData[] = [
                {
                    id: "cnc_001",
                    name: "CNC Mill #1",
                    type: "cnc",
                    status: "idle",
                    currentLot: undefined,
                    progress: 0,
                    facility: "Italy",
                    throughput: 0,
                    lastUpdate: new Date(),
                },
                {
                    id: "lathe_001",
                    name: "Lathe #1",
                    type: "tornio",
                    status: "idle",
                    currentLot: undefined,
                    progress: 0,
                    facility: "Brazil",
                    throughput: 0,
                    lastUpdate: new Date(),
                },
                {
                    id: "assembly_001",
                    name: "Assembly Line #1",
                    type: "assemblaggio",
                    status: "idle",
                    currentLot: undefined,
                    progress: 0,
                    facility: "Vietnam",
                    throughput: 0,
                    lastUpdate: new Date(),
                },
                {
                    id: "test_001",
                    name: "Testing Station #1",
                    type: "test",
                    status: "idle",
                    currentLot: undefined,
                    progress: 0,
                    facility: "Italy",
                    throughput: 0,
                    lastUpdate: new Date(),
                },
            ];
            setMachines(mockMachines);
        }
    }, [data?.machine_utilization, machines.length]);

    return (
        <div
            className={`min-h-screen p-4 ${retroMode ? "retro-mode" : "bg-gradient-to-br from-blue-50 to-indigo-100"}`}
            style={retroMode ? ({ "--retro-intensity": retroIntensity / 100 } as React.CSSProperties) : {}}
        >
            <div className="container mx-auto max-w-7xl">
                {/* Header */}
                <header className="mb-6">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-3">
                            <Factory className="h-8 w-8 text-blue-600" />
                            <div>
                                <h1 className="text-3xl font-bold text-gray-900">
                                    MokaMetrics Simulator Control Panel
                                </h1>
                                <p className="text-gray-600">
                                    Ultra Fast Testing Mode - 40-second total production cycles
                                </p>
                                <p className="text-sm text-gray-500">Kafka Broker: 165.227.168.240:29093</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            {/* Connection Status */}
                            <div className="flex items-center gap-2">
                                {connected ? (
                                    <Wifi className="h-4 w-4 text-green-500" />
                                ) : (
                                    <WifiOff className="h-4 w-4 text-red-500" />
                                )}
                                <Badge variant={connected ? "default" : "destructive"}>
                                    {connected ? "Connected" : "Disconnected"}
                                </Badge>
                            </div>

                            {/* Quick Start Button */}
                            {!data?.simulator_running && connected && (
                                <Button
                                    onClick={handleStartSimulator}
                                    className="bg-green-600 hover:bg-green-700 text-white font-semibold px-6"
                                >
                                    <Play className="h-4 w-4 mr-2" />
                                    Quick Start
                                </Button>
                            )}

                            {/* Simple Retro Toggle for Header */}
                            <Button variant="outline" size="sm" onClick={() => setRetroMode(!retroMode)}>
                                {retroMode ? "🖥️ Normal" : "🕹️ Retro"}
                            </Button>

                            {lastUpdate && (
                                <div className="text-sm text-gray-500">
                                    Last update: {lastUpdate.toLocaleTimeString()}
                                </div>
                            )}
                        </div>
                    </div>
                </header>

                {/* Error Display */}
                {error && (
                    <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-red-700">Connection Error: {error}</p>
                    </div>
                )}

                {/* Simulator Controls */}
                <div className="mb-6">
                    <SimulatorControls
                        isRunning={data?.simulator_running || false}
                        isConnected={connected}
                        onStart={handleStartSimulator}
                        onStop={handleStopSimulator}
                    />
                </div>

                {/* Main Dashboard Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                    {/* System Status */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">System Status</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {data?.simulator_running ? "🟢 Running" : "⚪ Stopped"}
                            </div>
                            <p className="text-xs text-muted-foreground">Uptime: {data?.uptime_formatted || "--"}</p>
                        </CardContent>
                    </Card>

                    {/* Total Lots */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Total Lots</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{data?.total_lots_completed || 0}</div>
                            <p className="text-xs text-muted-foreground">Completed lots</p>
                        </CardContent>
                    </Card>

                    {/* Messages/Second */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Messages/Sec</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{data?.messages_per_second || 0}</div>
                            <p className="text-xs text-muted-foreground">Real-time rate</p>
                        </CardContent>
                    </Card>

                    {/* Messages/Minute */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Messages/Min</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{data?.messages_per_minute || 0}</div>
                            <p className="text-xs text-muted-foreground">Average rate</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Production Chart */}
                <div className="mb-6">
                    <ProductionChart
                        data={productionData}
                        title="Real-time Production Rate"
                        yAxisLabel="Messages/Min"
                        color="rgb(59, 130, 246)"
                    />
                </div>

                {/* Machine Status Grid */}
                <div className="mb-6">
                    <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                        <Factory className="h-5 w-5" />
                        Machine Status
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {machines.map((machine) => (
                            <MachineStatusCard
                                key={machine.id}
                                machine={machine}
                                onMaintenance={handleMachineMaintenance}
                            />
                        ))}
                    </div>
                </div>

                {/* Phase 3: Advanced Features Grid */}
                <div className="mb-6">
                    <h2 className="text-xl font-semibold mb-4">Advanced Features</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {/* Coffee Bean Mascot */}
                        <CoffeeBeanMascot
                            messagesPerSecond={data?.messages_per_second || 0}
                            totalMessages={data?.total_lots_completed || 0}
                            isActive={data?.simulator_running || false}
                        />

                        {/* Enhanced Retro Effects Control */}
                        <RetroEffectsControl
                            onRetroModeChange={handleRetroModeChange}
                            onEffectIntensityChange={handleRetroIntensityChange}
                        />

                        {/* Lot Processing Panel */}
                        <LotProcessingPanel
                            onAddLot={handleAddLot}
                            onStartProcessing={handleStartProcessing}
                            isConnected={connected}
                            isSimulatorRunning={data?.simulator_running || false}
                        />
                    </div>
                </div>

                {/* Debug Info */}
                <div className="text-center py-6 text-gray-500 border-t">
                    <p className="text-sm">
                        Connected: {connected ? "✅" : "❌"} | Data: {data ? "✅" : "❌"} | Last Update:{" "}
                        {lastUpdate?.toLocaleTimeString() || "Never"}
                    </p>
                    <p className="text-xs mt-2">
                        Phase 3 Complete: Animated Mascot, Enhanced Retro Effects, Lot Processing
                    </p>
                </div>
            </div>
        </div>
    );
}

export default App;
