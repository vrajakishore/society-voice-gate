const CATEGORIES = [
  '', 'gate_security', 'lift', 'plumbing', 'electrical',
  'parking', 'housekeeping', 'noise', 'maintenance', 'emergency', 'general',
]
const STATUSES = ['', 'open', 'assigned', 'in_progress', 'resolved', 'closed']

interface Filters {
  category: string
  status: string
}

interface Props {
  filters: Filters
  onChange: (f: Filters) => void
  totalCount: number
}

export function FilterBar({ filters, onChange, totalCount }: Props) {
  const set = (key: keyof Filters, value: string) => onChange({ ...filters, [key]: value })

  return (
    <div style={styles.bar}>
      <span style={styles.count}>{totalCount} complaint{totalCount !== 1 ? 's' : ''}</span>

      <label style={styles.label}>Category</label>
      <select style={styles.select} value={filters.category} onChange={(e) => set('category', e.target.value)}>
        {CATEGORIES.map((c) => <option key={c} value={c}>{c ? c.replace(/_/g, ' ') : 'All categories'}</option>)}
      </select>

      <label style={styles.label}>Status</label>
      <select style={styles.select} value={filters.status} onChange={(e) => set('status', e.target.value)}>
        {STATUSES.map((s) => <option key={s} value={s}>{s ? s.replace(/_/g, ' ') : 'All statuses'}</option>)}
      </select>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  bar: { display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb', flexWrap: 'wrap' },
  count: { fontSize: 13, color: '#6b7280', marginRight: 8 },
  label: { fontSize: 12, fontWeight: 600, color: '#374151' },
  select: { padding: '5px 8px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, background: '#fff' },
}
