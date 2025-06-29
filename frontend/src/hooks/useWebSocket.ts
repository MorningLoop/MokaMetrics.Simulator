import { useState, useEffect, useRef, useCallback } from 'react'

export interface SimulatorStats {
  uptime_formatted?: string
  total_lots_completed?: number
  messages_per_second?: number
  messages_per_minute?: number
  simulator_running?: boolean
  machines?: Record<string, any>
  topics?: Record<string, any>
  [key: string]: any
}

export interface WebSocketState {
  data: SimulatorStats | null
  connected: boolean
  error: string | null
  lastUpdate: Date | null
}

export function useWebSocket(url?: string): WebSocketState & {
  sendMessage: (message: any) => void
  reconnect: () => void
} {
  const [state, setState] = useState<WebSocketState>({
    data: null,
    connected: false,
    error: null,
    lastUpdate: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  // Default to current host WebSocket URL
  const wsUrl = url || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`

  const connect = useCallback(() => {
    try {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        return
      }

      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setState(prev => ({
          ...prev,
          connected: true,
          error: null,
        }))
        reconnectAttemptsRef.current = 0
      }

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setState(prev => ({
            ...prev,
            data,
            lastUpdate: new Date(),
            error: null,
          }))
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
          setState(prev => ({
            ...prev,
            error: 'Failed to parse message',
          }))
        }
      }

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        setState(prev => ({
          ...prev,
          connected: false,
        }))

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            connect()
          }, delay)
        } else {
          setState(prev => ({
            ...prev,
            error: 'Max reconnection attempts reached',
          }))
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setState(prev => ({
          ...prev,
          error: 'Connection error',
        }))
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setState(prev => ({
        ...prev,
        error: 'Failed to connect',
      }))
    }
  }, [wsUrl])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    reconnectAttemptsRef.current = 0
    connect()
  }, [connect])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  return {
    ...state,
    sendMessage,
    reconnect,
  }
}
