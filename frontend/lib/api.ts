const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor(baseURL: string) {
    this.baseURL = baseURL
    
    // Get token from localStorage if available
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token')
    }
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        return {
          error: errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        }
      }

      const data = await response.json()
      return { data }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error'
      }
    }
  }

  // Auth endpoints
  async getCurrentUser() {
    return this.request('/auth/me')
  }

  // Repository endpoints
  async getRepositories() {
    return this.request('/repos/')
  }

  async getConnectedRepositories() {
    return this.request('/repos/connected')
  }

  async connectRepository(repoId: number) {
    return this.request(`/repos/${repoId}/connect`, {
      method: 'POST'
    })
  }

  // Scan endpoints
  async startScan(repoId: number) {
    return this.request(`/scan/start/${repoId}`, {
      method: 'POST'
    })
  }

  async getScanResults(scanId: number) {
    return this.request(`/scan/${scanId}`)
  }

  async getVulnerabilityFix(vulnId: number) {
    return this.request(`/scan/vulnerability/${vulnId}/fix`)
  }

  // PR endpoints
  async createFixPR(scanId: number) {
    return this.request(`/pr/create/${scanId}`, {
      method: 'POST'
    })
  }

  async getPRHistory() {
    return this.request('/pr/history')
  }
}

export const api = new ApiClient(API_BASE_URL)

// Types
export interface Repository {
  id: number
  name: string
  full_name: string
  private: boolean
  language: string
  default_branch: string
  updated_at: string
  clone_url: string
  html_url: string
}

export interface ConnectedRepository {
  id: number
  name: string
  url: string
  default_branch: string
  is_private: boolean
  created_at: string
}

export interface Vulnerability {
  id: number
  type: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  file_path: string
  line_number?: number
  message: string
  fixable: boolean
  confidence_score: number
  created_at: string
}

export interface Scan {
  id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string
  finished_at?: string
  issues_found: number
}

export interface ScanResults {
  scan: Scan
  repository: {
    id: number
    name: string
  }
  vulnerabilities: Vulnerability[]
  summary: {
    total_issues: number
    critical: number
    high: number
    medium: number
    low: number
    fixable: number
  }
}

export interface PullRequest {
  id: number
  pr_url: string
  branch_name: string
  status: string
  fixes_applied: number
  created_at: string
  repository: string
  scan_id: number
}