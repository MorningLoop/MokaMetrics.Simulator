import { Settings, Activity, Clock, Package } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

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
}

interface MachineStatusCardProps {
  machine: MachineData
  onMaintenance?: (machineId: string) => void
}

export function MachineStatusCard({ machine, onMaintenance }: MachineStatusCardProps) {
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

        {/* Maintenance Button */}
        {onMaintenance && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => onMaintenance(machine.id)}
            disabled={machine.status === 'maintenance'}
          >
            <Settings className="h-4 w-4 mr-2" />
            {machine.status === 'maintenance' ? 'In Maintenance' : 'Maintenance'}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
