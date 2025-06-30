import { useState, useEffect } from 'react'
import { Package, Clock, User, MapPin, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface LotDetail {
  id: string
  customer: string
  quantity: number
  status: 'pending' | 'in_progress' | 'completed' | 'error'
  currentMachine?: string
  progress: number
  orderDate: string
  deadline?: string
  estimatedCompletion?: string
  location: string
}

interface LotDetailPanelProps {
  isConnected: boolean
  isSimulatorRunning: boolean
}

export function LotDetailPanel({ 
  isConnected, 
  isSimulatorRunning 
}: LotDetailPanelProps) {
  const [lots, setLots] = useState<LotDetail[]>([])
  const [selectedLot, setSelectedLot] = useState<LotDetail | null>(null)

  // Mock data for demonstration
  useEffect(() => {
    if (isConnected && isSimulatorRunning) {
      const mockLots: LotDetail[] = [
        {
          id: 'LOT-001',
          customer: 'Acme Corp',
          quantity: 150,
          status: 'in_progress',
          currentMachine: 'CNC Italy',
          progress: 65,
          orderDate: '2024-01-15',
          deadline: '2024-01-20',
          estimatedCompletion: '2024-01-19',
          location: 'Italy'
        },
        {
          id: 'LOT-002',
          customer: 'TechStart Inc',
          quantity: 75,
          status: 'in_progress',
          currentMachine: 'Lathe Brazil',
          progress: 35,
          orderDate: '2024-01-16',
          deadline: '2024-01-22',
          estimatedCompletion: '2024-01-21',
          location: 'Brazil'
        },
        {
          id: 'LOT-003',
          customer: 'Global Manufacturing',
          quantity: 200,
          status: 'completed',
          progress: 100,
          orderDate: '2024-01-14',
          deadline: '2024-01-18',
          estimatedCompletion: '2024-01-17',
          location: 'Vietnam'
        },
        {
          id: 'LOT-004',
          customer: 'Precision Parts Ltd',
          quantity: 120,
          status: 'in_progress',
          currentMachine: 'Test Vietnam',
          progress: 80,
          orderDate: '2024-01-17',
          deadline: '2024-01-23',
          estimatedCompletion: '2024-01-22',
          location: 'Vietnam'
        },
        {
          id: 'LOT-005',
          customer: 'Industrial Solutions',
          quantity: 90,
          status: 'pending',
          progress: 0,
          orderDate: '2024-01-18',
          deadline: '2024-01-25',
          location: 'Italy'
        }
      ]
      setLots(mockLots)
      if (!selectedLot && mockLots.length > 0) {
        setSelectedLot(mockLots[0])
      }
    } else {
      setLots([])
      setSelectedLot(null)
    }
  }, [isConnected, isSimulatorRunning])

  const getStatusIcon = (status: LotDetail['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'in_progress':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: LotDetail['status']) => {
    const variants = {
      pending: 'secondary',
      in_progress: 'default',
      completed: 'default',
      error: 'destructive'
    } as const

    const colors = {
      pending: 'bg-gray-100 text-gray-800',
      in_progress: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800'
    }

    return (
      <Badge variant={variants[status]} className={colors[status]}>
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Package className="h-4 w-4 text-blue-600" />
          Lot Details
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {!isConnected ? (
          <div className="text-center py-4 text-muted-foreground">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
            <p className="text-sm">Not connected to simulator</p>
          </div>
        ) : !isSimulatorRunning ? (
          <div className="text-center py-4 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 text-gray-400" />
            <p className="text-sm">Simulator not running</p>
            <p className="text-xs">Start the simulator to view lot details</p>
          </div>
        ) : lots.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground">
            <Package className="h-8 w-8 mx-auto mb-2 text-gray-400" />
            <p className="text-sm">No lots in queue</p>
          </div>
        ) : (
          <>
            {/* Lot Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Active Lots ({lots.length})</label>
              <div className="grid grid-cols-1 gap-1 max-h-32 overflow-y-auto">
                {lots.map((lot) => (
                  <Button
                    key={lot.id}
                    onClick={() => setSelectedLot(lot)}
                    variant={selectedLot?.id === lot.id ? "default" : "ghost"}
                    size="sm"
                    className="justify-start h-auto p-2"
                  >
                    <div className="flex items-center gap-2 w-full">
                      {getStatusIcon(lot.status)}
                      <div className="flex-1 text-left">
                        <div className="font-medium text-xs">{lot.id}</div>
                        <div className="text-xs text-muted-foreground">{lot.customer}</div>
                      </div>
                      <div className="text-xs">{lot.quantity}</div>
                    </div>
                  </Button>
                ))}
              </div>
            </div>

            {/* Selected Lot Details */}
            {selectedLot && (
              <div className="space-y-3 border-t pt-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-sm">{selectedLot.id}</h4>
                  {getStatusBadge(selectedLot.status)}
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <User className="h-3 w-3 text-gray-500" />
                    <span className="text-xs text-muted-foreground">Customer:</span>
                    <span className="font-medium">{selectedLot.customer}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Package className="h-3 w-3 text-gray-500" />
                    <span className="text-xs text-muted-foreground">Quantity:</span>
                    <span className="font-medium">{selectedLot.quantity} units</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <MapPin className="h-3 w-3 text-gray-500" />
                    <span className="text-xs text-muted-foreground">Location:</span>
                    <span className="font-medium">{selectedLot.location}</span>
                  </div>

                  {selectedLot.currentMachine && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3 text-gray-500" />
                      <span className="text-xs text-muted-foreground">Machine:</span>
                      <span className="font-medium">{selectedLot.currentMachine}</span>
                    </div>
                  )}

                  {/* Progress Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium">{selectedLot.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${selectedLot.progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Dates */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">Ordered:</span>
                      <div className="font-medium">{formatDate(selectedLot.orderDate)}</div>
                    </div>
                    {selectedLot.deadline && (
                      <div>
                        <span className="text-muted-foreground">Deadline:</span>
                        <div className="font-medium">{formatDate(selectedLot.deadline)}</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
