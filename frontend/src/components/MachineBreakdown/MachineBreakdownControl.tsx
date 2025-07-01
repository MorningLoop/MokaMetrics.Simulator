import React, { useState, useEffect } from 'react';
import { AlertTriangle, RotateCcw, Settings, Activity } from 'lucide-react';
import { useMachineBreakdownStore, BREAKDOWN_TYPES, SEVERITY_LEVELS } from '../../stores/machineBreakdownStore';
import { apiService, handleApiCall } from '../../services/api';

export const MachineBreakdownControl: React.FC = () => {
  const {
    simulationEnabled,
    breakdownRate,
    stats,
    selectedBreakdownType,
    selectedSeverity,
    setSimulationEnabled,
    setBreakdownRate,
    setSelectedBreakdownType,
    setSelectedSeverity,
    updateStats,
    reset
  } = useMachineBreakdownStore();

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  // Fetch breakdown stats and config periodically
  useEffect(() => {
    const fetchData = async () => {
      // Fetch stats
      await handleApiCall(
        () => apiService.getBreakdownStats(),
        (data: any) => {
          if (data.stats) {
            updateStats(data.stats);
          }
        },
        (error) => console.error('Failed to fetch breakdown stats:', error)
      );

      // Fetch current config and sync with store
      await handleApiCall(
        () => apiService.getBreakdownConfig(),
        (data: any) => {
          if (data.config) {
            const config = data.config;
            setSimulationEnabled(config.enabled);
            setBreakdownRate(config.breakdown_rate_per_hour);
          }
        },
        (error) => console.error('Failed to fetch breakdown config:', error)
      );
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, [updateStats, setSimulationEnabled, setBreakdownRate]);

  const showMessage = (text: string, type: 'success' | 'error' = 'success') => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(null), 3000);
  };

  const handleResetAllMachines = async () => {
    setLoading(true);
    try {
      await handleApiCall(
        () => apiService.resetAllMachines(),
        (data: any) => {
          showMessage(`Reset ${data.reset_count || 0} machines from breakdown state`);
        },
        (error) => showMessage(`Failed to reset machines: ${error}`, 'error')
      );
    } finally {
      setLoading(false);
    }
  };

  const handleResetSimulation = async () => {
    reset();
    // Also reset on backend
    await handleApiCall(
      () => apiService.updateBreakdownConfig({ enabled: false, breakdown_rate_per_hour: 0 }),
      () => showMessage('Machine breakdown simulation settings reset'),
      (error) => showMessage(`Failed to reset settings: ${error}`, 'error')
    );
  };

  const handleToggleSimulation = async (enabled: boolean) => {
    setSimulationEnabled(enabled);
    await handleApiCall(
      () => apiService.updateBreakdownConfig({ enabled }),
      () => showMessage(`Breakdown simulation ${enabled ? 'enabled' : 'disabled'}`),
      (error) => showMessage(`Failed to update simulation: ${error}`, 'error')
    );
  };

  const handleRateChange = async (rate: number) => {
    setBreakdownRate(rate);
    await handleApiCall(
      () => apiService.updateBreakdownConfig({ breakdown_rate_per_hour: rate }),
      () => {}, // No message for rate changes to avoid spam
      (error) => showMessage(`Failed to update rate: ${error}`, 'error')
    );
  };

  return (
    <div className="bg-orange-50 border border-orange-300 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-orange-800 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          Machine Breakdown Simulation
        </h3>
        <div className="flex gap-2">
          <button
            onClick={handleResetAllMachines}
            disabled={loading}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm disabled:opacity-50"
          >
            <RotateCcw className="h-4 w-4 mr-1 inline" />
            Reset All Machines
          </button>
          <button
            onClick={handleResetSimulation}
            className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors text-sm"
          >
            <Settings className="h-4 w-4 mr-1 inline" />
            Reset Settings
          </button>
        </div>
      </div>

      {/* Message Display */}
      {message && (
        <div className={`mb-4 p-3 rounded-lg ${
          messageType === 'success' 
            ? 'bg-green-100 text-green-700 border border-green-200' 
            : 'bg-red-100 text-red-700 border border-red-200'
        }`}>
          {message}
        </div>
      )}

      <div className="space-y-4">
        {/* Simulation Toggle */}
        <div className="flex items-center justify-between">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={simulationEnabled}
              onChange={(e) => handleToggleSimulation(e.target.checked)}
              className="mr-2 h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
            />
            <span className="text-sm font-medium text-gray-700">
              Enable Random Machine Breakdowns
            </span>
          </label>
          {simulationEnabled && (
            <span className="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
              <Activity className="h-3 w-3 inline mr-1" />
              Active
            </span>
          )}
        </div>

        {/* Breakdown Rate Control */}
        {simulationEnabled && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Breakdown Rate: {breakdownRate}% chance per hour
            </label>
            <input
              type="range"
              min="0"
              max="50"
              value={breakdownRate}
              onChange={(e) => handleRateChange(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0% (No breakdowns)</span>
              <span>25%</span>
              <span>50% (Very frequent)</span>
            </div>
          </div>
        )}

        {/* Manual Breakdown Controls */}
        <div className="border-t pt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Manual Breakdown Trigger</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Breakdown Type
              </label>
              <select
                value={selectedBreakdownType}
                onChange={(e) => setSelectedBreakdownType(e.target.value)}
                className="w-full text-sm border border-gray-300 rounded px-2 py-1 focus:ring-orange-500 focus:border-orange-500"
              >
                {BREAKDOWN_TYPES.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Severity
              </label>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="w-full text-sm border border-gray-300 rounded px-2 py-1 focus:ring-orange-500 focus:border-orange-500"
              >
                {SEVERITY_LEVELS.map(level => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          <p className="text-xs text-gray-500 mt-2">
            Click on individual machine cards to trigger breakdowns with these settings.
          </p>
        </div>

        {/* Breakdown Statistics */}
        {stats && (
          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Current Status</h4>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-gray-900">{stats.total_machines}</div>
                <div className="text-xs text-gray-500">Total Machines</div>
              </div>
              
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-green-600">{stats.operational_machines}</div>
                <div className="text-xs text-gray-500">Operational</div>
              </div>
              
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-red-600">{stats.broken_machines}</div>
                <div className="text-xs text-gray-500">Broken</div>
              </div>
              
              <div className="bg-white p-2 rounded border">
                <div className="text-lg font-bold text-orange-600">{stats.breakdown_rate.toFixed(1)}%</div>
                <div className="text-xs text-gray-500">Breakdown Rate</div>
              </div>
            </div>

            {/* Breakdown by Type */}
            {Object.keys(stats.breakdown_by_type).length > 0 && (
              <div className="mt-3">
                <div className="text-xs font-medium text-gray-600 mb-1">Breakdowns by Type:</div>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(stats.breakdown_by_type).map(([type, count]) => (
                    <span key={type} className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                      {type}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};