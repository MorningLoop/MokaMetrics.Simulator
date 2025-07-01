// API service for communicating with the Python backend

const API_BASE_URL = '/api'

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
}

export interface LotData {
  customer: string
  quantity: number
  location?: string
  orderDate?: string
  deadline?: string
}

export interface MachineMaintenanceRequest {
  machineId: string
  action: 'start' | 'complete'
}

export interface MachineBreakdownRequest {
  machine_id: string
  location: string
  breakdown_type?: string
  reason?: string
  severity?: string
}

export interface MachineResetRequest {
  machine_id: string
  location: string
}

class ApiService {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }
    }
  }

  // Simulator control methods
  async startSimulator(): Promise<ApiResponse> {
    return this.request('/start', {
      method: 'POST',
    })
  }

  async stopSimulator(): Promise<ApiResponse> {
    return this.request('/stop', {
      method: 'POST',
    })
  }

  async getStatus(): Promise<ApiResponse> {
    return this.request('/status')
  }

  async getMachines(): Promise<ApiResponse> {
    return this.request('/machines')
  }

  // Lot management methods
  async addLot(lotData: LotData): Promise<ApiResponse> {
    return this.request('/add_lot', {
      method: 'POST',
      body: JSON.stringify(lotData),
    })
  }

  async startProcessing(): Promise<ApiResponse> {
    return this.request('/start_processing', {
      method: 'POST',
    })
  }

  // Machine maintenance methods
  async machineMaintenance(request: MachineMaintenanceRequest): Promise<ApiResponse> {
    return this.request('/machine_maintenance', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // Machine breakdown methods
  async triggerMachineBreakdown(request: MachineBreakdownRequest): Promise<ApiResponse> {
    return this.request('/machine/breakdown', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async resetMachineBreakdown(request: MachineResetRequest): Promise<ApiResponse> {
    return this.request('/machine/reset', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async resetAllMachines(): Promise<ApiResponse> {
    return this.request('/machines/reset-all', {
      method: 'POST',
    })
  }

  async getBreakdownStats(): Promise<ApiResponse> {
    return this.request('/machines/breakdown-stats')
  }

  async updateBreakdownConfig(config: { enabled?: boolean; breakdown_rate_per_hour?: number }): Promise<ApiResponse> {
    return this.request('/breakdown/config', {
      method: 'POST',
      body: JSON.stringify(config),
    })
  }

  async getBreakdownConfig(): Promise<ApiResponse> {
    return this.request('/breakdown/config')
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch('/health', { 
        method: 'GET',
        timeout: 5000 
      } as RequestInit)
      return response.ok
    } catch {
      return false
    }
  }
}

export const apiService = new ApiService()

// Helper function to handle API responses with error handling
export async function handleApiCall<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  onSuccess?: (data: T) => void,
  onError?: (error: string) => void
): Promise<boolean> {
  const response = await apiCall()
  
  if (response.success && response.data) {
    onSuccess?.(response.data)
    return true
  } else {
    onError?.(response.error || 'Unknown error occurred')
    return false
  }
}
