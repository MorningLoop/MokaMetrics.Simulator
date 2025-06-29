import { useState, useEffect } from 'react'
import { Monitor, RotateCcw, Palette } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface RetroEffectsControlProps {
  onRetroModeChange: (enabled: boolean) => void
  onEffectIntensityChange: (intensity: number) => void
}

export function RetroEffectsControl({ 
  onRetroModeChange, 
  onEffectIntensityChange 
}: RetroEffectsControlProps) {
  const [retroEnabled, setRetroEnabled] = useState(false)
  const [intensity, setIntensity] = useState(0)
  const [currentTheme, setCurrentTheme] = useState<'green' | 'amber' | 'blue' | 'purple'>('green')

  const themes = {
    green: {
      name: 'Classic Green',
      bg: '#001100',
      text: '#00ff00',
      glow: '#00ff00',
      emoji: '🟢'
    },
    amber: {
      name: 'Amber Terminal',
      bg: '#1a0f00',
      text: '#ffaa00',
      glow: '#ffaa00',
      emoji: '🟡'
    },
    blue: {
      name: 'Blue Matrix',
      bg: '#000011',
      text: '#0099ff',
      glow: '#0099ff',
      emoji: '🔵'
    },
    purple: {
      name: 'Purple Haze',
      bg: '#110011',
      text: '#aa00ff',
      glow: '#aa00ff',
      emoji: '🟣'
    }
  }

  const toggleRetroMode = () => {
    const newRetroEnabled = !retroEnabled
    setRetroEnabled(newRetroEnabled)
    onRetroModeChange(newRetroEnabled)
    
    if (newRetroEnabled && intensity === 0) {
      setIntensity(50)
      onEffectIntensityChange(50)
    }
  }

  const handleIntensityChange = (newIntensity: number) => {
    setIntensity(newIntensity)
    onEffectIntensityChange(newIntensity)
    
    if (newIntensity > 0 && !retroEnabled) {
      setRetroEnabled(true)
      onRetroModeChange(true)
    } else if (newIntensity === 0 && retroEnabled) {
      setRetroEnabled(false)
      onRetroModeChange(false)
    }
  }

  const cycleTheme = () => {
    const themeKeys = Object.keys(themes) as Array<keyof typeof themes>
    const currentIndex = themeKeys.indexOf(currentTheme)
    const nextIndex = (currentIndex + 1) % themeKeys.length
    setCurrentTheme(themeKeys[nextIndex])
  }

  const resetEffects = () => {
    setRetroEnabled(false)
    setIntensity(0)
    setCurrentTheme('green')
    onRetroModeChange(false)
    onEffectIntensityChange(0)
  }

  // Apply CSS custom properties for theming
  useEffect(() => {
    if (retroEnabled) {
      const theme = themes[currentTheme]
      const root = document.documentElement
      
      root.style.setProperty('--retro-bg', theme.bg)
      root.style.setProperty('--retro-text', theme.text)
      root.style.setProperty('--retro-glow', theme.glow)
      root.style.setProperty('--retro-intensity', (intensity / 100).toString())
    }
  }, [retroEnabled, currentTheme, intensity])

  const getIntensityLabel = () => {
    if (intensity >= 80) return 'Maximum'
    if (intensity >= 60) return 'High'
    if (intensity >= 40) return 'Medium'
    if (intensity >= 20) return 'Low'
    return 'Off'
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Monitor className="h-4 w-4 text-blue-600" />
          Retro Terminal Effects
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Main Toggle */}
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium">Retro Mode</div>
            <div className="text-sm text-muted-foreground">
              {retroEnabled ? 'Active' : 'Disabled'}
            </div>
          </div>
          <Button
            onClick={toggleRetroMode}
            variant={retroEnabled ? "default" : "outline"}
            size="sm"
          >
            {retroEnabled ? "🕹️ ON" : "🖥️ OFF"}
          </Button>
        </div>

        {/* Intensity Slider */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <label className="text-sm font-medium">Intensity</label>
            <Badge variant="outline">
              {getIntensityLabel()} ({intensity}%)
            </Badge>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={intensity}
            onChange={(e) => handleIntensityChange(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
          />
          <div className="text-xs text-muted-foreground">
            Adjust the retro terminal effect intensity
          </div>
        </div>

        {/* Theme Selector */}
        {retroEnabled && (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">Theme</label>
              <Button
                onClick={cycleTheme}
                variant="outline"
                size="sm"
              >
                <Palette className="h-4 w-4 mr-1" />
                {themes[currentTheme].emoji}
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">
              Current: {themes[currentTheme].name}
            </div>
          </div>
        )}

        {/* Quick Presets */}
        <div className="grid grid-cols-3 gap-2">
          <Button
            onClick={() => handleIntensityChange(25)}
            variant="outline"
            size="sm"
            className="text-xs"
          >
            Subtle
          </Button>
          <Button
            onClick={() => handleIntensityChange(50)}
            variant="outline"
            size="sm"
            className="text-xs"
          >
            Classic
          </Button>
          <Button
            onClick={() => handleIntensityChange(100)}
            variant="outline"
            size="sm"
            className="text-xs"
          >
            Extreme
          </Button>
        </div>

        {/* Reset Button */}
        <Button
          onClick={resetEffects}
          variant="ghost"
          size="sm"
          className="w-full"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset All Effects
        </Button>

        {/* Effect Preview */}
        {retroEnabled && (
          <div 
            className="p-3 rounded border text-center text-sm font-mono"
            style={{
              backgroundColor: themes[currentTheme].bg,
              color: themes[currentTheme].text,
              textShadow: `0 0 ${intensity / 20}px ${themes[currentTheme].glow}`,
              opacity: intensity / 100
            }}
          >
            &gt; RETRO_MODE_ACTIVE
          </div>
        )}
      </CardContent>
    </Card>
  )
}
