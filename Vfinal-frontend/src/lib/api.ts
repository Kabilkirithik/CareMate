// CareMate API Client
// Handles all communication with the Vfinal backend

const API_BASE_URL = (typeof window !== 'undefined' && (window as any).VITE_API_URL) || 
                   (import.meta as any).env?.VITE_API_URL || 
                   'http://localhost:8000'

export interface ChatRequest {
  patient_id: string
  message: string
}

export interface ChatResponse {
  session_id: string
  transcript?: string
  response_text: string
  response_audio_url?: string
  intent: string
}

export interface VoiceResponse extends ChatResponse {
  detected_language?: string
  detected_script?: string
}

class CareMateAPI {
  private baseURL: string
  private token: string | null = null

  constructor() {
    this.baseURL = API_BASE_URL
    this.token = typeof window !== 'undefined' ? localStorage.getItem('caremate_token') : null
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('caremate_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('caremate_token')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  // Health check
  async healthCheck(): Promise<{ status: string; database: string; agents: string }> {
    return this.request('/health')
  }

  // Chat endpoint
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // Voice endpoint
  async sendVoiceMessage(patientId: string, audioFile: File): Promise<VoiceResponse> {
    // Validate file before sending
    if (!audioFile) {
      throw new Error('No audio file provided')
    }

    if (audioFile.size === 0) {
      throw new Error('Audio file is empty')
    }

    if (audioFile.size < 100) {
      throw new Error('Audio file too small - likely invalid')
    }

    // Check file type (basic validation)
    const allowedTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/m4a', 'audio/webm', 'audio/ogg']
    if (audioFile.type && !allowedTypes.includes(audioFile.type)) {
      console.warn(`Unsupported audio type: ${audioFile.type}, but proceeding anyway`)
    }

    const formData = new FormData()
    formData.append('file', audioFile)

    // Extended timeout for AI processing
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 90000) // 90 seconds

    try {
      const response = await fetch(`${this.baseURL}/voice?patient_id=${patientId}`, {
        method: 'POST',
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` }),
        },
        body: formData,
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        let errorMessage = `Voice API Error: ${response.status}`
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorMessage
        } catch {
          errorMessage = await response.text() || errorMessage
        }
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error: any) {
      clearTimeout(timeoutId)
      if (error.name === 'AbortError') {
        throw new Error('Voice processing is taking longer than expected. Your message was received and is being processed.')
      }
      throw error
    }
  }

  // Authentication endpoints (to be implemented in backend)
  async login(email: string, password: string): Promise<{ token: string; user: any }> {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' })
    } finally {
      this.clearToken()
    }
  }

  // Doctor endpoints
  async getDoctorQueries(): Promise<{ queries: any[] }> {
    // No staff_id filter — show all doctor-intent queries
    // Per-doctor filtering will work once staff log in with their own credentials
    return this.request('/doctor/queries')
  }

  // Nurse endpoints
  async getNurseQueries(): Promise<{ queries: any[] }> {
    return this.request('/nurse/queries')
  }

  // Nutrition endpoints
  async getNutritionQueries(): Promise<{ queries: any[] }> {
    return this.request('/nutrition/queries')
  }

  // Utility endpoints
  async getUtilityQueries(): Promise<{ queries: any[] }> {
    return this.request('/utility/queries')
  }

  async getStaffAssignment(staffId: string): Promise<{ assignment: any }> {
    return this.request(`/staff/${staffId}/assignment`)
  }

  async getStaffDirectory(role?: string): Promise<{ staff: any[] }> {
    const query = role ? `?role=${role}` : ''
    return this.request(`/staff/directory${query}`)
  }

  private getCurrentUser(): { id: string; name: string; role: string } | null {
    if (typeof window === 'undefined') return null
    try {
      const stored = localStorage.getItem('caremate_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  // Public method to get current user
  public getUser(): { id: string; name: string; role: string } | null {
    return this.getCurrentUser()
  }

  async sendDoctorVoiceResponse(patientId: string, audioBlob: Blob): Promise<any> {
    const formData = new FormData()
    formData.append('file', audioBlob, 'response.mp3')

    const response = await fetch(`${this.baseURL}/doctor/voice-response?patient_id=${patientId}`, {
      method: 'POST',
      headers: {
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Doctor Voice Response Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  async sendDoctorTextResponse(data: any): Promise<any> {
    return this.request('/doctor/text-response', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Nurse endpoints
  async getNurseDocuments(): Promise<{ documents: any[] }> {
    return this.request('/nurse/documents')
  }

  async getNurseAssignments(): Promise<{ assignments: any[] }> {
    return this.request('/nurse/assignments')
  }

  async uploadDocument(patientId: string, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${this.baseURL}/nurse/upload-document?patient_id=${patientId}`, {
      method: 'POST',
      headers: {
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Document Upload Error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  // Patient endpoints
  async getPatientInfo(patientId: string): Promise<{ patient: any }> {
    return this.request(`/patients/${patientId}`)
  }

  async getPatientVitals(patientId: string): Promise<{ vitals: any[] }> {
    return this.request(`/patients/${patientId}/vitals`)
  }

  async getPatientMedications(patientId: string): Promise<{ medications: any[] }> {
    return this.request(`/patients/${patientId}/medications`)
  }

  async getPatientNotes(patientId: string): Promise<{ notes: any[] }> {
    return this.request(`/patients/${patientId}/notes`)
  }

  // Nutrition endpoints
  async getNutritionPlans(): Promise<{ plans: any[] }> {
    return this.request('/nutrition/plans')
  }

  async getNutritionMeals(date: string): Promise<{ meals: any[] }> {
    return this.request(`/nutrition/meals?date=${date}`)
  }

  async getNutritionAlerts(): Promise<{ alerts: any[] }> {
    return this.request('/nutrition/alerts')
  }

  // Utility endpoints
  async getMaintenanceRequests(): Promise<{ requests: any[] }> {
    return this.request('/utility/maintenance')
  }

  async getSystemStatuses(): Promise<{ systems: any[] }> {
    return this.request('/utility/systems')
  }

  async getUtilityAlerts(): Promise<{ alerts: any[] }> {
    return this.request('/utility/alerts')
  }

  // Admin endpoints
  async getSystemMetrics(): Promise<{ metrics: any }> {
    return this.request('/admin/metrics')
  }

  async getUserActivities(range: string): Promise<{ activities: any[] }> {
    return this.request(`/admin/activities?range=${range}`)
  }

  async getSystemAlerts(): Promise<{ alerts: any[] }> {
    return this.request('/admin/alerts')
  }

  async getUsers(): Promise<{ users: any[] }> {
    return this.request('/admin/users')
  }

  async resolveInteraction(interactionId: string): Promise<any> {
    return this.request(`/interactions/${interactionId}/resolve`, { method: 'POST' })
  }

  async respondInteraction(interactionId: string): Promise<any> {
    return this.request(`/interactions/${interactionId}/respond`, { method: 'POST' })
  }
}

// Export singleton instance
export const api = new CareMateAPI()

// Export types
export type { ChatRequest, ChatResponse, VoiceResponse }