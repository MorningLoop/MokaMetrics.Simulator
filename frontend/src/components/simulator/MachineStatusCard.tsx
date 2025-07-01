import { Settings, Activity, Clock, Package, AlertTriangle, RotateCcw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useMachineBreakdownStore } from '../../stores/machineBreakdownStore'
import { apiService, handleApiCall } from '../../services/api'
import { useState } from 'react'

export interface MachineData {
  id: string
  name: string
  type: string
  status: 'running' | 'idle' | 'maintenance' | 'error'
  currentLot?: string
  progress?: number
  lastUpdate?: Date
  facility?: string
  throughput?: number
  // Breakdown-specific fields
  breakdown_type?: string
  breakdown_reason?: string
  breakdown_severity?: string
  breakdown_duration?: number
}

interface MachineStatusCardProps {
  machine: MachineData
  onMaintenance?: (machineId: string) => void
}

export function MachineStatusCard({ machine, onMaintenance }: MachineStatusCardProps) {
  const { selectedBreakdownType, selectedSeverity } = useMachineBreakdownStore();
  const [loading, setLoading] = useState(false);

  const handleTriggerBreakdown = async () => {
    if (!machine.facility) return;
    
    setLoading(true);
    try {
      await handleApiCall(
        () => apiService.triggerMachineBreakdown({
          machine_id: machine.id,
          location: machine.facility!,
          breakdown_type: selectedBreakdownType,
          severity: selectedSeverity,
          reason: `Manual ${selectedBreakdownType} breakdown triggered`
        }),
        () => console.log(`Breakdown triggered on ${machine.id}`),
        (error) => console.error(`Failed to trigger breakdown: ${error}`)
      );
    } finally {
      setLoading(false);
    }
  };

  const handleResetBreakdown = async () => {
    if (!machine.facility) return;
    
    setLoading(true);
    try {
      await handleApiCall(
        () => apiService.resetMachineBreakdown({
          machine_id: machine.id,
          location: machine.facility!
        }),
        () => console.log(`Reset breakdown on ${machine.id}`),
        (error) => console.error(`Failed to reset breakdown: ${error}`)
      );
    } finally {
      setLoading(false);
    }
  };
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'default'
      case 'idle':
        return 'secondary'
      case 'maintenance':
        return 'outline'
      case 'error':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return '🟢'
      case 'idle':
        return '🟡'
      case 'maintenance':
        return '🔧'
      case 'error':
        return '🔴'
      default:
        return '⚪'
    }
  }

  const formatMachineType = (type: string) => {
    const typeMap: Record<string, string> = {
      'fresa_cnc': 'CNC Milling',
      'cnc': 'CNC Milling',
      'tornio': 'Lathe',
      'lathe': 'Lathe',
      'assemblaggio': 'Assembly',
      'assembly': 'Assembly',
      'test': 'Testing'
    }
    return typeMap[type] || type
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">
            {machine.name || `Machine ${machine.id}`}
          </CardTitle>
          <Badge variant={getStatusColor(machine.status)}>
            {machine.status}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {formatMachineType(machine.type)}
        </p>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Status Icon and Current Lot */}
        <div className="flex items-center justify-between">
          <div className="text-3xl">
            {getStatusIcon(machine.status)}
          </div>
          <div className="text-right">
            <div className="font-semibold">
              {machine.currentLot || '--'}
            </div>
            <p className="text-xs text-muted-foreground">Current Lot</p>
          </div>
        </div>

        {/* Progress Bar */}
        {machine.progress !== undefined && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{machine.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${machine.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Machine Details */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          {machine.facility && (
            <div className="flex items-center gap-2">
              <Package className="h-4 w-4 text-gray-500" />
              <span className="text-muted-foreground">{machine.facility}</span>
            </div>
          )}
          
          {machine.throughput !== undefined && (
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-gray-500" />
              <span className="text-muted-foreground">{machine.throughput}/min</span>
            </div>
          )}
          
          {machine.lastUpdate && (
            <div className="flex items-center gap-2 col-span-2">
              <Clock className="h-4 w-4 text-gray-500" />
              <span className="text-muted-foreground text-xs">
                Last update: {machine.lastUpdate.toLocaleTimeString()}
              </span>
            </div>
          )}
        </div>

        {/* Breakdown Information */}
        {machine.status === 'error' && (machine.breakdown_type || machine.breakdown_reason) && (
          <div className="bg-red-50 border border-red-200 rounded p-3 space-y-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <span className="text-sm font-semibold text-red-800">Machine Breakdown</span>
            </div>
            
            {machine.breakdown_type && (
              <div className="text-xs">
                <span className="font-medium">Type:</span> {machine.breakdown_type}
              </div>
            )}
            
            {machine.breakdown_reason && (
              <div className="text-xs">
                <span className="font-medium">Reason:</span> {machine.breakdown_reason}
              </div>
            )}
            
            {machine.breakdown_severity && (
              <div className="text-xs">
                <span className="font-medium">Severity:</span> 
                <span className={`ml-1 px-2 py-0.5 rounded text-xs ${
                  machine.breakdown_severity === 'critical' ? 'bg-red-200 text-red-800' :
                  machine.breakdown_severity === 'major' ? 'bg-orange-200 text-orange-800' :
                  'bg-yellow-200 text-yellow-800'
                }`}>
                  {machine.breakdown_severity}
                </span>
              </div>
            )}
            
            {machine.breakdown_duration && (
              <div className="text-xs">
                <span className="font-medium">Duration:</span> {machine.breakdown_duration.toFixed(1)} min
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-2">
          {/* Maintenance Button */}
          {onMaintenance && (
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => onMaintenance(machine.id)}
              disabled={machine.status === 'maintenance' || loading}
            >
              <Settings className="h-4 w-4 mr-2" />
              {machine.status === 'maintenance' ? 'In Maintenance' : 'Maintenance'}
            </Button>
          )}
          
          {/* Breakdown Control Buttons */}
          {machine.status === 'error' ? (
            <Button
              variant="default"
              size="sm"
              className="w-full bg-green-600 hover:bg-green-700"
              onClick={handleResetBreakdown}
              disabled={loading}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              {loading ? 'Resetting...' : 'Reset Breakdown'}
            </Button>
          ) : (
            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={handleTriggerBreakdown}
              disabled={machine.status === 'maintenance' || loading}
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              {loading ? 'Triggering...' : 'Trigger Breakdown'}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
