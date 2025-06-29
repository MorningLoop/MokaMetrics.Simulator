import { useState } from 'react'
import { Play, Square, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface SimulatorControlsProps {
  isRunning: boolean
  isConnected: boolean
  onStart: () => Promise<void>
  onStop: () => Promise<void>
}

export function SimulatorControls({ 
  isRunning, 
  isConnected, 
  onStart, 
  onStop 
}: SimulatorControlsProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async () => {
    if (!isConnected) {
      setError('Cannot start simulator: Not connected to backend')
      return
    }

    setIsLoading(true)
    setError(null)
    
    try {
      await onStart()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start simulator')
    } finally {
      setIsLoading(false)
    }
  }

  const handleStop = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      await onStop()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop simulator')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-5 w-5 text-green-600" />
          Simulator Control
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Display */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {isRunning ? "🟢" : "⚪"}
            </div>
            <div>
              <Badge variant={isRunning ? "default" : "secondary"}>
                {isRunning ? "Running" : "Stopped"}
              </Badge>
              <p className="text-sm text-muted-foreground mt-1">
                {isConnected ? "Backend connected" : "Backend disconnected"}
              </p>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Control Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleStart}
            disabled={isRunning || !isConnected || isLoading}
            className="flex-1"
            variant="default"
          >
            {isLoading && !isRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Start Simulator
          </Button>
          
          <Button
            onClick={handleStop}
            disabled={!isRunning || isLoading}
            className="flex-1"
            variant="destructive"
          >
            {isLoading && isRunning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Square className="h-4 w-4 mr-2" />
            )}
            Stop Simulator
          </Button>
        </div>

        {/* Quick Info */}
        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Ultra Fast Testing Mode: 40-second production cycles</p>
          <p>• Kafka Broker: 165.227.168.240:29093</p>
          <p>• API Endpoint: {isConnected ? "Connected" : "Disconnected"}</p>
        </div>
      </CardContent>
    </Card>
  )
}
