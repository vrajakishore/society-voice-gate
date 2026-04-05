import type { Ticket } from '../types'

const PRIORITY_COLOR: Record<string, string> = {
  emergency: '#dc2626',
  high: '#ea580c',
  medium: '#d97706',
  low: '#16a34a',
}

const STATUS_BG: Record<string, string> = {
  open: '#dbeafe',
  assigned: '#e0e7ff',
  in_progress: '#fef3c7',
  resolved: '#dcfce7',
  closed: '#f3f4f6',
}

interface Props {
  tickets: Ticket[]
  onSelect: (t: Ticket) => void
  selectedId?: string
}

export function TicketList({ tickets, onSelect, selectedId }: Props) {
  if (tickets.length === 0) {
    return <div style={styles.empty}>No complaints yet. Waiting for incoming voice calls…</div>
  }

  return (
    <table style={styles.table}>
      <thead>
        <tr style={styles.headerRow}>
          {['ID', 'Category', 'Location', 'Caller', 'Priority', 'Status', 'Created'].map((h) => (
            <th key={h} style={styles.th}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {tickets.map((t) => (
          <tr
            key={t.id}
            onClick={() => onSelect(t)}
            style={{ ...styles.row, background: t.id === selectedId ? '#eff6ff' : '#fff' }}
          >
            <td style={{ ...styles.td, fontWeight: 600, fontFamily: 'monospace' }}>{t.id}</td>
            <td style={styles.td}>{t.category.replace(/_/g, ' ')}</td>
            <td style={styles.td}>{t.location || '—'}</td>
            <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: 12 }}>{t.caller_phone || '—'}</td>
            <td style={styles.td}>
              <span style={{ color: PRIORITY_COLOR[t.priority], fontWeight: 600, fontSize: 12 }}>
                {t.priority.toUpperCase()}
              </span>
            </td>
            <td style={styles.td}>
              <span style={{ ...styles.statusBadge, background: STATUS_BG[t.status] ?? '#f3f4f6' }}>
                {t.status.replace(/_/g, ' ')}
              </span>
            </td>
            <td style={{ ...styles.td, color: '#6b7280', fontSize: 12 }}>
              {new Date(t.created_at).toLocaleString()}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const styles: Record<string, React.CSSProperties> = {
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  headerRow: { background: '#f9fafb' },
  th: { textAlign: 'left', padding: '10px 14px', fontWeight: 600, fontSize: 12, color: '#6b7280', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb', whiteSpace: 'nowrap' },
  row: { cursor: 'pointer', borderBottom: '1px solid #e5e7eb', transition: 'background 0.1s' },
  td: { padding: '12px 14px', verticalAlign: 'middle' },
  statusBadge: { borderRadius: 4, padding: '2px 7px', fontSize: 11, whiteSpace: 'nowrap', color: '#374151' },
  empty: { padding: 40, textAlign: 'center', color: '#9ca3af', fontSize: 14 },
}
