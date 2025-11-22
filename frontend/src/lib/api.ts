import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export interface Topic {
  id: string
  label: string
  count: number
  sample_titles: string[]
  sources: string[]
  confidence: number
}

export interface TrendsResponse {
  country: string
  generated_at: string
  topics: Topic[]
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get('/health')
  return response.data
}

export const getTopTrends = async (
  country: string,
  limit: number = 10
): Promise<TrendsResponse> => {
  const response = await api.get('/v1/trends/top', {
    params: { country, limit },
  })
  return response.data
}

export default api
