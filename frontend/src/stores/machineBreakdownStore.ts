import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface BreakdownStats {
  total_machines: number;
  broken_machines: number;
  operational_machines: number;
  breakdown_rate: number;
  breakdown_by_type: Record<string, number>;
  breakdown_by_severity: Record<string, number>;
  breakdown_by_location: Record<string, {
    total: number;
    broken: number;
    operational: number;
  }>;
}

interface MachineBreakdownState {
  // Breakdown simulation settings
  simulationEnabled: boolean;
  breakdownRate: number; // 0-100 percentage chance per hour
  
  // Statistics
  stats: BreakdownStats | null;
  lastStatsUpdate: Date | null;
  
  // Manual breakdown settings
  selectedBreakdownType: string;
  selectedSeverity: string;
  
  // Actions
  setSimulationEnabled: (enabled: boolean) => void;
  setBreakdownRate: (rate: number) => void;
  setSelectedBreakdownType: (type: string) => void;
  setSelectedSeverity: (severity: string) => void;
  updateStats: (stats: BreakdownStats) => void;
  reset: () => void;
}

// Available breakdown types
export const BREAKDOWN_TYPES = [
  { value: 'mechanical', label: 'Mechanical Failure' },
  { value: 'electrical', label: 'Electrical Issue' },
  { value: 'software', label: 'Software/Control Issue' },
  { value: 'tooling', label: 'Tooling Problem' },
  { value: 'overheating', label: 'Thermal Issue' }
];

// Available severity levels
export const SEVERITY_LEVELS = [
  { value: 'minor', label: 'Minor' },
  { value: 'major', label: 'Major' },
  { value: 'critical', label: 'Critical' }
];

export const useMachineBreakdownStore = create<MachineBreakdownState>()(
  persist(
    (set) => ({
      // Initial state
      simulationEnabled: false,
      breakdownRate: 10, // 10% chance per hour
      stats: null,
      lastStatsUpdate: null,
      selectedBreakdownType: 'mechanical',
      selectedSeverity: 'minor',
      
      // Actions
      setSimulationEnabled: (enabled) => set({ simulationEnabled: enabled }),
      
      setBreakdownRate: (rate) => {
        // Ensure rate is between 0 and 100
        const clampedRate = Math.max(0, Math.min(100, rate));
        set({ breakdownRate: clampedRate });
      },
      
      setSelectedBreakdownType: (type) => set({ selectedBreakdownType: type }),
      
      setSelectedSeverity: (severity) => set({ selectedSeverity: severity }),
      
      updateStats: (stats) => set({ 
        stats, 
        lastStatsUpdate: new Date() 
      }),
      
      reset: () => set({
        simulationEnabled: false,
        breakdownRate: 10,
        stats: null,
        lastStatsUpdate: null,
        selectedBreakdownType: 'mechanical',
        selectedSeverity: 'minor'
      })
    }),
    {
      name: 'machine-breakdown-storage',
      // Only persist user preferences, not real-time stats
      partialize: (state) => ({
        simulationEnabled: state.simulationEnabled,
        breakdownRate: state.breakdownRate,
        selectedBreakdownType: state.selectedBreakdownType,
        selectedSeverity: state.selectedSeverity
      })
    }
  )
);