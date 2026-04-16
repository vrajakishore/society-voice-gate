import axios from 'axios'
import type { Ticket } from './types'

const api = axios.create({ baseURL: '/api' })

export interface TicketFilters {
  category?: string
  status?: string
  limit?: number
}

export const listTickets = (filters: TicketFilters = {}): Promise<Ticket[]> =>
  api.get('/tickets', { params: filters }).then((r) => r.data)

export const getTicket = (id: string): Promise<Ticket> =>
  api.get(`/tickets/${id}`).then((r) => r.data)

export const updateTicket = (
  id: string,
  update: Partial<{ status: string; assigned_to: string; resolution_notes: string }>
): Promise<Ticket> =>
  api.patch(`/tickets/${id}`, update).then((r) => r.data)

export const requestCallback = (phone: string): Promise<{ call_id: string; status: string }> =>
  api.post('/callback', { phone }).then((r) => r.data)

export interface ServiceHealth {
  name: string
  status: string
  detail: string
}

export interface HealthResponse {
  overall: string
  services: ServiceHealth[]
}

export const getHealthServices = (): Promise<HealthResponse> =>
  api.get('/health/services').then((r) => r.data)
