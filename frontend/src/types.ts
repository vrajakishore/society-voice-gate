export interface Ticket {
  id: string
  channel: 'voice'
  category: string
  sub_category: string
  priority: 'low' | 'medium' | 'high' | 'emergency'
  location: string
  caller_phone: string
  description: string
  status: 'open' | 'assigned' | 'in_progress' | 'resolved' | 'closed'
  assigned_to: string
  created_at: string
  last_updated_at: string
  transcript: string
  resolution_notes: string
  source_call_id: string
  events: { type: string; at: string; note?: string }[]
}
