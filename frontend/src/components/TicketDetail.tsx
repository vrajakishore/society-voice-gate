import { useState } from 'react'
import type { Ticket } from '../types'
import { updateTicket } from '../api'

const STATUSES = ['open', 'assigned', 'in_progress', 'resolved', 'closed']

interface Props {
  ticket: Ticket
  onClose: () => void
  onUpdated: (t: Ticket) => void
}

export function TicketDetail({ ticket, onClose, onUpdated }: Props) {
  const [status, setStatus] = useState(ticket.status)
  const [assignedTo, setAssignedTo] = useState(ticket.assigned_to)
  const [notes, setNotes] = useState(ticket.resolution_notes ?? '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateTicket(ticket.id, {
        status,
        assigned_to: assignedTo,
        resolution_notes: notes,
      })
      onUpdated(updated)
    } finally {
      setSaving(false)
    }
  }

  const priorityColor: Record<string, string> = {
    emergency: '#dc2626',
    high: '#ea580c',
    medium: '#d97706',
    low: '#16a34a',
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.panel}>
        <div style={styles.header}>
          <span style={styles.ticketId}>{ticket.id}</span>
          <span style={styles.channelBadge}>📞 Voice</span>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        <div style={styles.section}>
          <Row label="Category" value={ticket.category.replace(/_/g, ' ')} />
          <Row label="Sub-category" value={ticket.sub_category || '—'} />
          <Row label="Location" value={ticket.location || '—'} />
          <Row
            label="Priority"
            value={<span style={{ color: priorityColor[ticket.priority], fontWeight: 600 }}>{ticket.priority.toUpperCase()}</span>}
          />
          <Row label="Caller phone" value={ticket.caller_phone || '—'} />
          <Row label="Created" value={new Date(ticket.created_at).toLocaleString()} />
          {ticket.description && <Row label="Description" value={ticket.description} />}
        </div>

        <div style={styles.section}>
          <label style={styles.label}>Status</label>
          <select value={status} onChange={(e) => setStatus(e.target.value as Ticket['status'])} style={styles.select}>
            {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
          </select>

          <label style={styles.label}>Assigned to</label>
          <input value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)} style={styles.input} placeholder="Name or team" />

          <label style={styles.label}>Resolution notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} style={styles.textarea} rows={3} />

          <button onClick={handleSave} disabled={saving} style={styles.saveBtn}>
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>

        {ticket.transcript && (
          <div style={styles.section}>
            <label style={styles.label}>Call transcript</label>
            <pre style={styles.transcript}>{ticket.transcript}</pre>
          </div>
        )}

        {ticket.events?.length > 0 && (
          <div style={styles.section}>
            <label style={styles.label}>Timeline</label>
            {ticket.events.map((e, i) => (
              <div key={i} style={styles.timelineItem}>
                <span style={styles.timelineDot} />
                <span style={styles.timelineText}>
                  {e.type.replace(/_/g, ' ')}
                  {e.note ? ` — ${e.note}` : ''}
                  <span style={styles.timelineAt}> · {new Date(e.at).toLocaleString()}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={styles.row}>
      <span style={styles.rowLabel}>{label}</span>
      <span style={styles.rowValue}>{value}</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', justifyContent: 'flex-end', zIndex: 100 },
  panel: { width: 460, background: '#fff', overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 0 },
  header: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 },
  ticketId: { fontSize: 18, fontWeight: 700, flex: 1 },
  channelBadge: { color: '#fff', background: '#2563eb', borderRadius: 4, padding: '2px 8px', fontSize: 12 },
  closeBtn: { border: 'none', background: 'none', fontSize: 18, cursor: 'pointer', color: '#6b7280' },
  section: { borderTop: '1px solid #e5e7eb', paddingTop: 16, marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 },
  label: { fontSize: 12, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' },
  select: { padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 },
  input: { padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 },
  textarea: { padding: '6px 8px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, resize: 'vertical', fontFamily: 'inherit' },
  saveBtn: { padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, alignSelf: 'flex-start' },
  transcript: { background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: 12, fontSize: 12, whiteSpace: 'pre-wrap', maxHeight: 240, overflowY: 'auto', fontFamily: 'monospace' },
  row: { display: 'flex', gap: 8 },
  rowLabel: { fontSize: 13, color: '#6b7280', width: 130, flexShrink: 0 },
  rowValue: { fontSize: 13, fontWeight: 500 },
  timelineItem: { display: 'flex', alignItems: 'flex-start', gap: 8 },
  timelineDot: { width: 8, height: 8, borderRadius: '50%', background: '#2563eb', marginTop: 5, flexShrink: 0 },
  timelineText: { fontSize: 13 },
  timelineAt: { color: '#9ca3af', fontSize: 11 },
}
