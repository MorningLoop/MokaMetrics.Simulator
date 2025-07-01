import { useState, useEffect } from 'react'
import { Package, Clock, User, MapPin, CheckCircle, AlertCircle, Loader2, Trash2 } from 'lucide-react'
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
  completedPieces: number
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
  const [isRemoving, setIsRemoving] = useState(false)

  // Fetch real lots from API
  useEffect(() => {
    if (isConnected && isSimulatorRunning) {
      const fetchLots = async () => {
        try {
          const response = await fetch('/api/status')
          const data = await response.json()
          const activeLots = data.active_lots || []
          
          // Convert API lot format to component format
          const convertedLots: LotDetail[] = activeLots.map((lot: any) => ({
            id: lot.lot_code,
            customer: lot.customer,
            quantity: lot.quantity,
            status: mapStageToStatus(lot.current_stage),
            currentMachine: lot.current_machine || undefined,
            progress: lot.progress_percentage || calculateProgress(lot.current_stage), // Use real progress if available
            orderDate: lot.order_date || new Date().toISOString().split('T')[0],
            deadline: lot.deadline || undefined,
            estimatedCompletion: lot.estimated_completion || undefined,
            location: lot.location,
            completedPieces: lot.completed_pieces || 0
          }))
          
          setLots(convertedLots)
          if (!selectedLot && convertedLots.length > 0) {
            setSelectedLot(convertedLots[0])
          } else if (selectedLot && !convertedLots.find(l => l.id === selectedLot.id)) {
            setSelectedLot(convertedLots.length > 0 ? convertedLots[0] : null)
          }
        } catch (error) {
          console.error('Failed to fetch lots:', error)
          setLots([])
          setSelectedLot(null)
        }
      }
      
      fetchLots()
      
      // Refresh lots every 5 seconds
      const interval = setInterval(fetchLots, 5000)
      return () => clearInterval(interval)
    } else {
      setLots([])
      setSelectedLot(null)
    }
  }, [isConnected, isSimulatorRunning])

  // Remove lot function
  const removeLot = async (lotId: string) => {
    if (!lotId || isRemoving) return
    
    setIsRemoving(true)
    try {
      const response = await fetch('/api/delete_lot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lot_code: lotId })
      })
      
      if (response.ok) {
        // Refresh the lots list
        const statusResponse = await fetch('/api/status')
        const data = await statusResponse.json()
        const activeLots = data.active_lots || []
        
        const convertedLots: LotDetail[] = activeLots.map((lot: any) => ({
          id: lot.lot_code,
          customer: lot.customer,
          quantity: lot.quantity,
          status: mapStageToStatus(lot.current_stage),
          currentMachine: lot.current_machine || undefined,
          progress: lot.progress_percentage || calculateProgress(lot.current_stage),
          orderDate: lot.order_date || new Date().toISOString().split('T')[0],
          deadline: lot.deadline || undefined,
          estimatedCompletion: lot.estimated_completion || undefined,
          location: lot.location,
          completedPieces: lot.completed_pieces || 0
        }))
        
        setLots(convertedLots)
        
        // If the removed lot was selected, select a new one or clear selection
        if (selectedLot?.id === lotId) {
          setSelectedLot(convertedLots.length > 0 ? convertedLots[0] : null)
        }
      } else {
        console.error('Failed to remove lot')
      }
    } catch (error) {
      console.error('Error removing lot:', error)
    } finally {
      setIsRemoving(false)
    }
  }

  // Helper function to map API stage to component status
  const mapStageToStatus = (stage: string): LotDetail['status'] => {
    switch (stage) {
      case 'queued':
        return 'pending'
      case 'cnc':
      case 'lathe':
      case 'assembly':
      case 'test':
        return 'in_progress'
      case 'completed':
        return 'completed'
      default:
        return 'pending'
    }
  }

  // Helper function to calculate progress based on stage
  const calculateProgress = (stage: string): number => {
    switch (stage) {
      case 'queued':
        return 0
      case 'cnc':
        return 25
      case 'lathe':
        return 50
      case 'assembly':
        return 75
      case 'test':
        return 90
      case 'completed':
        return 100
      default:
        return 0
    }
  }

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
                  <div className="flex items-center gap-2">
                    {getStatusBadge(selectedLot.status)}
                    <Button
                      onClick={() => removeLot(selectedLot.id)}
                      disabled={isRemoving}
                      size="sm"
                      variant="outline"
                      className="h-6 w-6 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      {isRemoving ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Trash2 className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <User className="h-3 w-3 text-gray-500" />
                    <span className="text-xs text-muted-foreground">Customer:</span>
                    <span className="font-medium">{selectedLot.customer}</span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Package className="h-3 w-3 text-gray-500" />
                      <span className="text-xs text-muted-foreground">Quantity:</span>
                      <span className="font-medium">{selectedLot.quantity} units</span>
                    </div>
                    <div className="flex items-center gap-2 ml-5">
                      <span className="text-xs text-muted-foreground">Completed:</span>
                      <span className="font-medium text-blue-600">
                        {selectedLot.completedPieces}/{selectedLot.quantity}
                      </span>
                    </div>
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
