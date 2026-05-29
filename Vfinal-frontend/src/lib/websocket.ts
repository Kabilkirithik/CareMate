// CareMate WebSocket Client
// Handles real-time communication with the backend

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

export class CareMateWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Set<(data: any) => void>> = new Map()
  private isConnecting = false

  constructor(url?: string) {
    const defaultWsUrl = (typeof window !== 'undefined' && (window as any).VITE_WS_URL) || 
                         (import.meta as any).env?.VITE_WS_URL || 
                         'ws://localhost:8000/ws'
    this.url = url || defaultWsUrl
  }

  connect(token?: string, staffId?: string, role?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (this.isConnecting) {
        return
      }

      this.isConnecting = true
      
      try {
        // Build WebSocket URL with query parameters
        let wsUrl = this.url
        const params = new URLSearchParams()
        
        if (token) params.append('token', token)
        if (staffId) params.append('staff_id', staffId)
        if (role) params.append('role', role)
        
        if (params.toString()) {
          wsUrl = `${this.url}?${params.toString()}`
        }
        
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          console.log('CareMate WebSocket connected', { staffId, role })
          this.isConnecting = false
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('CareMate WebSocket disconnected:', event.code, event.reason)
          this.isConnecting = false
          this.ws = null
          
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect(token, staffId, role)
          }
        }

        this.ws.onerror = (error) => {
          console.error('CareMate WebSocket error:', error)
          this.isConnecting = false
          reject(error)
        }

      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  private scheduleReconnect(token?: string, staffId?: string, role?: string) {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      this.connect(token, staffId, role).catch(console.error)
    }, delay)
  }

  private handleMessage(message: WebSocketMessage) {
    const listeners = this.listeners.get(message.type)
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(message.data)
        } catch (error) {
          console.error(`Error in WebSocket listener for ${message.type}:`, error)
        }
      })
    }

    // Also trigger 'message' listeners for all messages
    const allListeners = this.listeners.get('message')
    if (allListeners) {
      allListeners.forEach(callback => {
        try {
          callback(message)
        } catch (error) {
          console.error('Error in WebSocket message listener:', error)
        }
      })
    }
  }

  on(eventType: string, callback: (data: any) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)!.add(callback)
  }

  off(eventType: string, callback: (data: any) => void) {
    const listeners = this.listeners.get(eventType)
    if (listeners) {
      listeners.delete(callback)
      if (listeners.size === 0) {
        this.listeners.delete(eventType)
      }
    }
  }

  send(type: string, data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type,
        data,
        timestamp: new Date().toISOString()
      }
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected. Message not sent:', { type, data })
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.listeners.clear()
    this.reconnectAttempts = 0
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get readyState(): number | undefined {
    return this.ws?.readyState
  }
}

// Export singleton instance
export const websocket = new CareMateWebSocket()