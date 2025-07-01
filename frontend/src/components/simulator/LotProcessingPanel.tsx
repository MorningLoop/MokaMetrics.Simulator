import { useState } from 'react'
import { Package, Plus, Play, Calendar, User, Hash, MapPin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface LotData {
  customer: string
  quantity: number
  location?: string
  orderDate?: string
  deadline?: string
}

interface LotProcessingPanelProps {
  onAddLot: (lot: LotData) => Promise<void>
  onStartProcessing: () => Promise<void>
  isConnected: boolean
  isSimulatorRunning: boolean
}

export function LotProcessingPanel({ 
  onAddLot, 
  onStartProcessing, 
  isConnected, 
  isSimulatorRunning 
}: LotProcessingPanelProps) {
  const [customer, setCustomer] = useState('')
  const [quantity, setQuantity] = useState<number>(1)
  const [location, setLocation] = useState('Italy')
  const [orderDate, setOrderDate] = useState('')
  const [deadline, setDeadline] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const validateForm = () => {
    if (!customer.trim()) return 'Customer name is required'
    if (quantity < 1 || quantity > 1000) return 'Quantity must be between 1 and 1000'
    if (orderDate && new Date(orderDate) > new Date()) return 'Order date cannot be in the future'
    if (deadline && orderDate && new Date(deadline) < new Date(orderDate)) {
      return 'Deadline cannot be before order date'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      const lotData: LotData = {
        customer: customer.trim(),
        quantity,
        location,
        orderDate: orderDate || undefined,
        deadline: deadline || undefined
      }

      await onAddLot(lotData)
      
      setSuccess(`Lot added successfully for ${customer} (${quantity} units) at ${location}`)
      
      // Reset form
      setCustomer('')
      setQuantity(1)
      setLocation('Italy')
      setOrderDate('')
      setDeadline('')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add lot')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleStartProcessing = async () => {
    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      await onStartProcessing()
      setSuccess('Processing started successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start processing')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getRandomCustomer = () => {
    const customers = [
      'Acme Coffee Co.',
      'Bean There Roasters',
      'Caffeine Dreams Ltd.',
      'Daily Grind Inc.',
      'Espresso Express',
      'Fresh Brew Corp.',
      'Golden Bean Co.',
      'Morning Glory Coffee'
    ]
    return customers[Math.floor(Math.random() * customers.length)]
  }

  const fillRandomData = () => {
    const locations = ['Italy', 'Brazil', 'Vietnam']
    
    setCustomer(getRandomCustomer())
    setQuantity(Math.floor(Math.random() * 50) + 10) // 10-59
    setLocation(locations[Math.floor(Math.random() * locations.length)])
    
    const today = new Date()
    const orderDate = new Date(today.getTime() - Math.random() * 7 * 24 * 60 * 60 * 1000) // Last 7 days
    const deadlineDate = new Date(today.getTime() + Math.random() * 30 * 24 * 60 * 60 * 1000) // Next 30 days
    
    setOrderDate(orderDate.toISOString().split('T')[0])
    setDeadline(deadlineDate.toISOString().split('T')[0])
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Package className="h-4 w-4 text-orange-600" />
          Lot Processing
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Status Indicators */}
        <div className="flex gap-2 flex-wrap">
          <Badge variant={isConnected ? "default" : "destructive"}>
            {isConnected ? "Connected" : "Disconnected"}
          </Badge>
          <Badge variant={isSimulatorRunning ? "default" : "secondary"}>
            {isSimulatorRunning ? "Running" : "Stopped"}
          </Badge>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
            {success}
          </div>
        )}
        
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Add Lot Form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-medium text-sm">Add New Lot</h3>
            <Button
              type="button"
              onClick={fillRandomData}
              variant="ghost"
              size="sm"
              className="text-xs"
            >
              Random Data
            </Button>
          </div>

          {/* Customer Input */}
          <div className="space-y-1">
            <label className="text-xs font-medium flex items-center gap-1">
              <User className="h-3 w-3" />
              Customer
            </label>
            <input
              type="text"
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
              placeholder="Enter customer name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Quantity Input */}
          <div className="space-y-1">
            <label className="text-xs font-medium flex items-center gap-1">
              <Hash className="h-3 w-3" />
              Quantity
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              min="1"
              max="1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Location Selector */}
          <div className="space-y-1">
            <label className="text-xs font-medium flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              Location
            </label>
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="Italy">🇮🇹 Italy</option>
              <option value="Brazil">🇧🇷 Brazil</option>
              <option value="Vietnam">🇻🇳 Vietnam</option>
            </select>
          </div>

          {/* Date Inputs */}
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="text-xs font-medium flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Order Date
              </label>
              <input
                type="date"
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
                className="w-full px-2 py-2 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="space-y-1">
              <label className="text-xs font-medium flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                Deadline
              </label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full px-2 py-2 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={!isConnected || isSubmitting}
            className="w-full"
            size="sm"
          >
            <Plus className="h-4 w-4 mr-2" />
            {isSubmitting ? 'Adding Lot...' : 'Add Lot'}
          </Button>
        </form>

        {/* Start Processing Button */}
        <div className="pt-2 border-t">
          <Button
            onClick={handleStartProcessing}
            disabled={!isConnected || !isSimulatorRunning || isSubmitting}
            variant="outline"
            className="w-full"
            size="sm"
          >
            <Play className="h-4 w-4 mr-2" />
            {isSubmitting ? 'Starting...' : 'Start Processing'}
          </Button>
          <p className="text-xs text-muted-foreground mt-1 text-center">
            Begins processing all queued lots
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
