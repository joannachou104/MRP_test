import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

const TRIGGER_LABEL = {
  lead_time_breach: '前置時間不足',
  below_safety_stock: '低於安全庫存',
  both: '前置時間不足 + 低於安全庫存',
}

export default function DashboardPage() {
  const [results, setResults] = useState([])
  const [products, setProducts] = useState([])
  const [runDate, setRunDate] = useState(null)
  const [category, setCategory] = useState('')
  const [triggerOnly, setTriggerOnly] = useState(true)
  const [recommendationType, setRecommendationType] = useState('')
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)
  const [reminders, setReminders] = useState([])

  const load = useCallback(async () => {
    setError('')
    try {
      const params = new URLSearchParams()
      if (category) params.set('category', category)
      if (triggerOnly) params.set('trigger_only', 'true')
      if (recommendationType) params.set('recommendation_type', recommendationType)
      const [res, prods, rd, rem] = await Promise.all([
        api.get(`/mrp/results?${params.toString()}`),
        api.get('/products'),
        api.get('/mrp/latest-run-date'),
        api.get('/mrp/arrival-reminders'),
      ])
      setResults(res)
      setProducts(prods)
      setRunDate(rd.run_date)
      setReminders(rem)
    } catch (e) {
      setError(e.message)
    }
  }, [category, triggerOnly, recommendationType])

  useEffect(() => { load() }, [load])

  async function runMrp() {
    setRunning(true)
    setError('')
    try {
      await api.post('/mrp/run')
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  function productInfo(id) {
    return products.find((p) => p.product_id === id)
  }

  const categories = [...new Set(products.map((p) => p.category).filter(Boolean))]

  const triggeredCount = results.filter((r) => r.trigger_reason).length
  const activeCount = results.filter((r) => r.recommendation_type === 'active' && r.trigger_reason).length
  const ignoredCount = results.filter((r) => r.review_status === 'ignored').length

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>MRP 運算儀表板</h1>
          <p className="page-desc">淨需求總覽、可銷售天數、缺貨警示。最近運算日期:{runDate || '尚未執行過運算'}</p>
        </div>
        <button className="primary" onClick={runMrp} disabled={running}>{running ? '運算中…' : '執行 MRP 運算'}</button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {reminders.length > 0 && (
        <div className="alert info">
          在途到貨提醒:{reminders.map((r) => `${r.product_id}(庫存增量 ${r.stock_increase} ≥ 在途量 ${r.pending_qty})`).join('、')} — 疑似已到貨,請至採購建議頁面確認。
        </div>
      )}

      <div className="stat-cards">
        <div className="stat-card"><div className="stat-value">{results.length}</div><div className="stat-label">顯示節點數</div></div>
        <div className="stat-card"><div className="stat-value">{triggeredCount}</div><div className="stat-label">觸發缺口</div></div>
        <div className="stat-card"><div className="stat-value">{activeCount}</div><div className="stat-label">主動建議</div></div>
        <div className="stat-card"><div className="stat-value">{ignoredCount}</div><div className="stat-label">已忽略</div></div>
      </div>

      <div className="panel">
        <div className="toolbar">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">全部分類</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={recommendationType} onChange={(e) => setRecommendationType(e.target.value)}>
            <option value="">全部類型</option>
            <option value="active">主動建議</option>
            <option value="reference">人工參考</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={triggerOnly} onChange={(e) => setTriggerOnly(e.target.checked)} />
            僅顯示有缺口的品項
          </label>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>商品</th><th>分類</th><th>供應商/通路</th><th>預測需求</th><th>目前庫存</th>
                <th>可銷售天數</th><th>淨需求</th><th>建議採購量</th><th>建議下單期限</th>
                <th>觸發原因</th><th>類型</th><th>審閱狀態</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const p = productInfo(r.product_id)
                return (
                  <tr key={r.result_id}>
                    <td>{r.product_id}<div className="muted">{p?.product_name}</div></td>
                    <td>{p?.category}</td>
                    <td>{p?.lead_time_type === 'procurement' ? p?.supplier_id : p?.processing_plant_id}</td>
                    <td>{r.forecast_demand}</td>
                    <td>{r.current_stock}</td>
                    <td>{r.sellable_days?.toFixed(2)}</td>
                    <td>{r.net_requirement > 0 ? <strong>{r.net_requirement}</strong> : 0}</td>
                    <td>{r.suggested_order_qty}</td>
                    <td>{r.suggested_order_deadline || '—'}</td>
                    <td>{r.trigger_reason ? <span className="badge warn">{TRIGGER_LABEL[r.trigger_reason]}</span> : <span className="badge ok">正常</span>}</td>
                    <td>{r.recommendation_type === 'active' ? <span className="badge ok">主動</span> : <span className="badge neutral">參考</span>}</td>
                    <td>{r.review_status === 'ignored' ? <span className="badge neutral">已忽略</span> : '—'}</td>
                  </tr>
                )
              })}
              {results.length === 0 && <tr><td colSpan={12} className="empty-state">尚無運算結果,請先執行 MRP 運算</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
