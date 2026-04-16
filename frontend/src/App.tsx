import { useCallback, useEffect, useRef, useState } from 'react'
import { listTickets, requestCallback } from './api'
import { FilterBar } from './components/FilterBar'
import { HealthDashboard } from './components/HealthDashboard'
import { TicketDetail } from './components/TicketDetail'
import { TicketList } from './components/TicketList'
import type { Ticket } from './types'
import './App.css'

type Tab = 'complaints' | 'health'

const POLL_INTERVAL_MS = 5000

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selected, setSelected] = useState<Ticket | null>(null)
  const [filters, setFilters] = useState({ category: '', status: '' })
  const [loading, setLoading] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [callbackPhone, setCallbackPhone] = useState('')
  const [callbackStatus, setCallbackStatus] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('complaints')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchTickets = useCallback(async () => {
    try {
      const params: Record<string, string> = {}
      if (filters.category) params.category = filters.category
      if (filters.status) params.status = filters.status
      const data = await listTickets(params)
      setTickets(data)
      setLastRefresh(new Date())
    } catch {
      // silently ignore transient network errors during polling
    }
  }, [filters])

  useEffect(() => {
    setLoading(true)
    fetchTickets().finally(() => setLoading(false))
    timerRef.current = setInterval(() => { fetchTickets() }, POLL_INTERVAL_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [fetchTickets])

  const handleTicketUpdated = (updated: Ticket) => {
    setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    setSelected(updated)
  }

  const openCounts = tickets.filter((t) => t.status === 'open').length

  const handleCallback = async () => {
    if (!callbackPhone.trim()) return
    setCallbackStatus('Calling…')
    try {
      await requestCallback(callbackPhone.trim())
      setCallbackStatus('Call placed! You should receive a call shortly.')
      setTimeout(() => setCallbackStatus(''), 5000)
    } catch {
      setCallbackStatus('Failed to place call.')
      setTimeout(() => setCallbackStatus(''), 5000)
    }
  }

  return (
    <div style={styles.root}>
      <div style={styles.sidebar}>
        <div style={styles.logo}>🏢 Society Voice Gate</div>
        <div
          style={activeTab === 'complaints' ? styles.navItemActive : styles.navItem}
          onClick={() => setActiveTab('complaints')}
        >📋 Complaints</div>
        <div
          style={activeTab === 'health' ? styles.navItemActive : styles.navItem}
          onClick={() => setActiveTab('health')}
        >🩺 App Health</div>
        <div style={{ flex: 1 }} />
        <div style={styles.sidebarFooter}>
          {lastRefresh && <span style={styles.refreshTime}>Updated {lastRefresh.toLocaleTimeString()}</span>}
        </div>
      </div>

      {activeTab === 'complaints' ? (
        <>
          <div style={styles.main}>
            <div style={styles.topbar}>
              <span style={styles.pageTitle}>Complaint Inbox</span>
              <div style={styles.topbarRight}>
                <input
                  type="tel"
                  placeholder="+91 98765 43210"
                  value={callbackPhone}
                  onChange={(e) => setCallbackPhone(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCallback()}
                  style={styles.phoneInput}
                />
                <button onClick={handleCallback} style={styles.callBtn} disabled={!callbackPhone.trim()}>
                  📞 Call Me
                </button>
                {callbackStatus && <span style={styles.callbackStatus}>{callbackStatus}</span>}
                {openCounts > 0 && <span style={styles.openBadge}>{openCounts} open</span>}
                <button onClick={() => fetchTickets()} style={styles.refreshBtn}>🔄 Refresh</button>
              </div>
            </div>

            <div style={styles.summaryRow}>
              {(['open', 'assigned', 'in_progress', 'resolved'] as const).map((s) => (
                <div key={s} style={styles.summaryCard}>
                  <div style={styles.summaryCount}>{tickets.filter((t) => t.status === s).length}</div>
                  <div style={styles.summaryLabel}>{s.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>

            <FilterBar filters={filters} onChange={setFilters} totalCount={tickets.length} />

            <div style={styles.tableWrapper}>
              {loading ? (
                <div style={styles.loadingMsg}>Loading…</div>
              ) : (
                <TicketList tickets={tickets} onSelect={setSelected} selectedId={selected?.id} />
              )}
            </div>
          </div>

          {selected && (
            <TicketDetail ticket={selected} onClose={() => setSelected(null)} onUpdated={handleTicketUpdated} />
          )}
        </>
      ) : (
        <div style={styles.main}>
          <HealthDashboard />
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: { display: 'flex', minHeight: '100vh', fontFamily: "'Inter', system-ui, sans-serif", background: '#f8fafc' },
  sidebar: { width: 220, background: '#1e293b', color: '#e2e8f0', display: 'flex', flexDirection: 'column', padding: '0 0 20px', flexShrink: 0 },
  logo: { fontSize: 15, fontWeight: 700, padding: '24px 20px 20px', borderBottom: '1px solid #334155' },
  navItem: { padding: '12px 20px', fontSize: 14, cursor: 'pointer', color: '#94a3b8', margin: '4px 10px', borderRadius: 6 },
  navItemActive: { padding: '12px 20px', fontSize: 14, cursor: 'pointer', background: '#2563eb', color: '#fff', margin: '4px 10px', borderRadius: 6 },
  sidebarFooter: { padding: '0 20px' },
  refreshTime: { fontSize: 10, color: '#64748b' },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  topbar: { display: 'flex', alignItems: 'center', padding: '16px 24px', background: '#fff', borderBottom: '1px solid #e5e7eb', gap: 12 },
  pageTitle: { fontSize: 20, fontWeight: 700, flex: 1, color: '#0f172a' },
  topbarRight: { display: 'flex', alignItems: 'center', gap: 10 },
  openBadge: { background: '#fef3c7', color: '#92400e', borderRadius: 12, padding: '2px 10px', fontSize: 12, fontWeight: 600 },
  refreshBtn: { padding: '6px 12px', border: '1px solid #d1d5db', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 13 },
  phoneInput: { padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, width: 160 },
  callBtn: { padding: '6px 12px', border: 'none', borderRadius: 6, background: '#16a34a', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  callbackStatus: { fontSize: 12, color: '#16a34a', maxWidth: 180 },
  summaryRow: { display: 'flex', gap: 16, padding: '16px 24px', background: '#fff', borderBottom: '1px solid #e5e7eb' },
  summaryCard: { textAlign: 'center', padding: '12px 24px', background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 8, minWidth: 90 },
  summaryCount: { fontSize: 28, fontWeight: 700, color: '#0f172a' },
  summaryLabel: { fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 },
  tableWrapper: { flex: 1, overflowY: 'auto', background: '#fff' },
  loadingMsg: { padding: 40, textAlign: 'center', color: '#9ca3af' },
}
