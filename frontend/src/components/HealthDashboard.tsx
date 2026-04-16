import { useCallback, useEffect, useState } from 'react'
import { getHealthServices, type ServiceHealth } from '../api'

const STATUS_ICON: Record<string, string> = {
  healthy: '🟢',
  degraded: '🟡',
  unhealthy: '🔴',
  unknown: '⚪',
  error: '🔴',
}

const STATUS_COLOR: Record<string, string> = {
  healthy: '#16a34a',
  degraded: '#d97706',
  unhealthy: '#dc2626',
  unknown: '#9ca3af',
  error: '#dc2626',
}

export function HealthDashboard() {
  const [services, setServices] = useState<ServiceHealth[]>([])
  const [overall, setOverall] = useState<string>('unknown')
  const [loading, setLoading] = useState(true)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getHealthServices()
      setServices(data.services)
      setOverall(data.overall)
      setLastCheck(new Date())
    } catch {
      setOverall('error')
      setServices([{ name: 'Health API', status: 'unhealthy', detail: 'Failed to reach /api/health/services' }])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return (
    <div style={{ padding: 24 }}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>App Health</h2>
          <span style={{ fontSize: 13, color: '#64748b' }}>
            Overall: <span style={{ fontWeight: 600, color: STATUS_COLOR[overall] }}>{STATUS_ICON[overall]} {overall.toUpperCase()}</span>
            {lastCheck && <> &middot; Last checked {lastCheck.toLocaleTimeString()}</>}
          </span>
        </div>
        <button onClick={refresh} disabled={loading} style={styles.refreshBtn}>
          {loading ? '⏳ Checking…' : '🔄 Refresh'}
        </button>
      </div>

      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Status</th>
            <th style={styles.th}>Service</th>
            <th style={styles.th}>Detail</th>
          </tr>
        </thead>
        <tbody>
          {services.map((s, i) => (
            <tr key={i} style={i % 2 === 0 ? styles.rowEven : styles.rowOdd}>
              <td style={{ ...styles.td, textAlign: 'center', fontSize: 18 }}>
                {STATUS_ICON[s.status] ?? '⚪'}
              </td>
              <td style={styles.td}>
                <span style={{ fontWeight: 600 }}>{s.name}</span>
                <br />
                <span style={{ fontSize: 11, color: STATUS_COLOR[s.status], fontWeight: 500, textTransform: 'uppercase' }}>
                  {s.status}
                </span>
              </td>
              <td style={{ ...styles.td, fontSize: 13, color: '#475569', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                {s.detail}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  title: { margin: '0 0 4px', fontSize: 20, fontWeight: 700, color: '#0f172a' },
  refreshBtn: { padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 13 },
  table: { width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' },
  th: { padding: '12px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '2px solid #e5e7eb', background: '#f8fafc' },
  td: { padding: '14px 16px', borderBottom: '1px solid #f1f5f9', verticalAlign: 'top' },
  rowEven: { background: '#fff' },
  rowOdd: { background: '#fafbfc' },
}
