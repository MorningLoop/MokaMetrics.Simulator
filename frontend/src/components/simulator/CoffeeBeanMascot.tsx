import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Sprout, Coffee, Zap } from 'lucide-react'

interface CoffeeBeanMascotProps {
  messagesPerSecond: number
  totalMessages: number
  isActive: boolean
}

type MascotStage = 'seed' | 'sprout' | 'plant' | 'coffee' | 'energized'

export function CoffeeBeanMascot({ 
  messagesPerSecond, 
  totalMessages, 
  isActive 
}: CoffeeBeanMascotProps) {
  const [stage, setStage] = useState<MascotStage>('seed')
  const [growth, setGrowth] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [clickCount, setClickCount] = useState(0)

  // Calculate growth based on total messages
  useEffect(() => {
    const newGrowth = Math.min(100, (totalMessages / 100) * 100) // 100 messages = 100% growth
    setGrowth(newGrowth)

    // Determine stage based on growth
    if (newGrowth >= 80) {
      setStage('energized')
    } else if (newGrowth >= 60) {
      setStage('coffee')
    } else if (newGrowth >= 40) {
      setStage('plant')
    } else if (newGrowth >= 20) {
      setStage('sprout')
    } else {
      setStage('seed')
    }
  }, [totalMessages])

  // Animate when messages are being sent
  useEffect(() => {
    if (messagesPerSecond > 0 && isActive) {
      setIsAnimating(true)
      const timer = setTimeout(() => setIsAnimating(false), 1000)
      return () => clearTimeout(timer)
    } else {
      setIsAnimating(false)
    }
  }, [messagesPerSecond, isActive])

  const getMascotEmoji = () => {
    switch (stage) {
      case 'seed':
        return '🌱'
      case 'sprout':
        return '🌿'
      case 'plant':
        return '☘️'
      case 'coffee':
        return '☕'
      case 'energized':
        return '⚡'
      default:
        return '🌱'
    }
  }

  const getStageDescription = () => {
    switch (stage) {
      case 'seed':
        return 'Seed Stage'
      case 'sprout':
        return 'Sprouting'
      case 'plant':
        return 'Growing'
      case 'coffee':
        return 'Coffee Ready!'
      case 'energized':
        return 'Energized!'
      default:
        return 'Seed Stage'
    }
  }

  const getStageColor = () => {
    switch (stage) {
      case 'seed':
        return 'bg-yellow-100 text-yellow-800'
      case 'sprout':
        return 'bg-green-100 text-green-800'
      case 'plant':
        return 'bg-green-200 text-green-900'
      case 'coffee':
        return 'bg-amber-100 text-amber-800'
      case 'energized':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleMascotClick = () => {
    setClickCount(prev => prev + 1)
    setIsAnimating(true)
    setTimeout(() => setIsAnimating(false), 500)
  }

  const getActivityLevel = () => {
    if (messagesPerSecond >= 10) return 'Very Active'
    if (messagesPerSecond >= 5) return 'Active'
    if (messagesPerSecond >= 1) return 'Working'
    return 'Idle'
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Sprout className="h-4 w-4 text-green-600" />
          Simulator Pet
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Mascot Display */}
        <div className="flex flex-col items-center">
          <div 
            className={`text-6xl cursor-pointer transition-all duration-300 ${
              isAnimating ? 'animate-bounce scale-110' : 'hover:scale-105'
            }`}
            onClick={handleMascotClick}
            title="Click me!"
          >
            {getMascotEmoji()}
          </div>
          
          {/* Stage Badge */}
          <div className={`mt-2 px-3 py-1 rounded-full text-xs font-semibold ${getStageColor()}`}>
            {getStageDescription()}
          </div>
        </div>

        {/* Growth Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Growth</span>
            <span>{Math.round(growth)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div 
              className={`h-3 rounded-full transition-all duration-500 ${
                stage === 'energized' ? 'bg-gradient-to-r from-purple-500 to-pink-500' :
                stage === 'coffee' ? 'bg-gradient-to-r from-amber-500 to-orange-500' :
                'bg-gradient-to-r from-green-400 to-green-600'
              }`}
              style={{ width: `${growth}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="text-center">
            <div className="font-bold text-lg">{totalMessages}</div>
            <div className="text-muted-foreground">Messages</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-lg">{clickCount}</div>
            <div className="text-muted-foreground">Pet Clicks</div>
          </div>
        </div>

        {/* Activity Status */}
        <div className="flex items-center justify-center gap-2 p-2 bg-gray-50 rounded-lg">
          {messagesPerSecond > 0 ? (
            <>
              <Zap className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium">{getActivityLevel()}</span>
            </>
          ) : (
            <>
              <Coffee className="h-4 w-4 text-gray-500" />
              <span className="text-sm text-muted-foreground">Resting</span>
            </>
          )}
        </div>

        {/* Fun Messages */}
        {stage === 'energized' && (
          <div className="text-center text-xs text-purple-600 font-medium animate-pulse">
            ⚡ Maximum Power! ⚡
          </div>
        )}
        
        {clickCount > 10 && (
          <div className="text-center text-xs text-blue-600 font-medium">
            🎉 Thanks for the attention! 🎉
          </div>
        )}
      </CardContent>
    </Card>
  )
}
