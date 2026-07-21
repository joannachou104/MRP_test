import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'
import { useUser } from '../context/UserContext'

const TABS = [
  { key: 'active', label: '主動建議清單' },
  { key: 'reference', label: '人工參考區' },
  { key: 'pending', label: '在途清單' },
]

export default function ProcurementPage() {
  const [tab, setTab] = useState('active')
  const [results, setResults] = useState({ active: [], reference: [] })
  const [pendingList, setPendingList] = useState([])
  const [reminders, setReminders] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [registerTarget, setRegisterTarget] = useState(null)
  const [arrivalTarget, setArrivalTarget] = useState(null)
  const { user } = useUser()

  const load = useCallback(async () => {
    setError('')
    try {
      const [active, ref, pend, rem] = await Promise.all([
        api.get('/mrp/results?trigger_only=true&recommendation_type=active'),
        api.get('/mrp/results?trigger_only=true&recommendation_type=reference'),
        api.get('/procurement/pending'),
        api.get('/mrp/arrival-reminders'),
      ])
      setResults({ active, reference: ref })
      setPendingList(pend)
      setReminders(rem)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function ignoreProduct(productId) {
    const note = prompt('忽略原因(選填):') || ''
    setError('')
    try {
      await api.post('/ignore', { product_id: productId, note })
      setNotice(`已將 ${productId} 加入忽略清單`)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function cancelPending(id) {
    if (!confirm('確定取消此在途紀錄?將直接刪除,不保留歷史。')) return
    setError('')
    try {
      await api.del(`/procurement/pending/${id}`)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const canOperate = user.role === 'admin' || user.role === 'procurement'

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>採購建議</h1>
          <p className="page-desc">主動建議清單、人工參考區、在途登記與到貨確認、忽略缺口設定。登記在途/確認到貨/忽略需商品管理或採購人員權限。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert success">{notice}</div>}
      {!canOperate && <div className="alert info">目前角色為唯讀訪客,登記在途/確認到貨/忽略等操作將被拒絕。</div>}

      {reminders.length > 0 && (
        <div className="alert info">
          {reminders.map((r) => `${r.product_id} 疑似已到貨(庫存增量 ${r.stock_increase} ≥ 在途量 ${r.pending_qty})`).join('、')}
        </div>
      )}

      <div className="tabs">
        {TABS.map((t) => (
          <div key={t.key} className={'tab' + (tab === t.key ? ' active' : '')} onClick={() => setTab(t.key)}>{t.label}</div>
        ))}
      </div>

      {(tab === 'active' || tab === 'reference') && (
        <div className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>商品</th><th>淨需求</th><th>建議採購量</th><th>建議下單期限</th><th>觸發原因</th><th>審閱狀態</th><th></th>
                </tr>
              </thead>
              <tbody>
                {(results[tab] || []).map((r) => (
                  <tr key={r.result_id}>
                    <td>{r.product_id}</td>
                    <td>{r.net_requirement}</td>
                    <td>{r.suggested_order_qty}</td>
                    <td>{r.suggested_order_deadline || '—'}</td>
                    <td>{r.trigger_reason}</td>
                    <td>{r.review_status === 'ignored' ? <span className="badge neutral">已忽略</span> : '未審閱'}</td>
                    <td>
                      <button disabled={!canOperate} onClick={() => setRegisterTarget(r)}>登記在途</button>{' '}
                      {r.review_status !== 'ignored' && (
                        <button disabled={!canOperate} onClick={() => ignoreProduct(r.product_id)}>忽略</button>
                      )}
                    </td>
                  </tr>
                ))}
                {(results[tab] || []).length === 0 && <tr><td colSpan={7} className="empty-state">目前無此類建議</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'pending' && (
        <div className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>商品</th><th>下單日期</th><th>預進貨日期</th><th>預進貨量</th><th>實際到貨量</th><th>狀態</th><th>登記人</th><th></th>
                </tr>
              </thead>
              <tbody>
                {pendingList.map((p) => (
                  <tr key={p.pending_id}>
                    <td>{p.product_id}</td>
                    <td>{p.order_date || '—'}</td>
                    <td>{p.expected_arrival_date || '—'}</td>
                    <td>{p.expected_qty}</td>
                    <td>{p.received_qty ?? '—'}</td>
                    <td>{p.status === 'pending' ? <span className="badge warn">待到貨</span> : <span className="badge ok">已到貨</span>}</td>
                    <td>{p.registered_by}</td>
                    <td>
                      {p.status === 'pending' && (
                        <>
                          <button disabled={!canOperate} onClick={() => setArrivalTarget(p)}>確認到貨</button>{' '}
                          <button className="danger" disabled={!canOperate} onClick={() => cancelPending(p.pending_id)}>取消</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
                {pendingList.length === 0 && <tr><td colSpan={8} className="empty-state">尚無在途紀錄</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {registerTarget && (
        <RegisterPendingModal
          result={registerTarget}
          onClose={() => setRegisterTarget(null)}
          onDone={() => { setRegisterTarget(null); load() }}
          setError={setError}
        />
      )}
      {arrivalTarget && (
        <ConfirmArrivalModal
          pending={arrivalTarget}
          onClose={() => setArrivalTarget(null)}
          onDone={() => { setArrivalTarget(null); load() }}
          setError={setError}
        />
      )}
    </div>
  )
}

function RegisterPendingModal({ result, onClose, onDone, setError }) {
  const [orderDate, setOrderDate] = useState(new Date().toISOString().slice(0, 10))
  const [arrivalDate, setArrivalDate] = useState('')
  const [qty, setQty] = useState(result.suggested_order_qty)

  async function submit(e) {
    e.preventDefault()
    try {
      await api.post('/procurement/pending', {
        product_id: result.product_id,
        source_result_id: result.result_id,
        order_date: orderDate || null,
        expected_arrival_date: arrivalDate || null,
        expected_qty: Number(qty),
      })
      onDone()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">登記在途採購 — {result.product_id}</div>
        <form onSubmit={submit}>
          <div className="form-grid">
            <div className="field"><label>下單日期</label><input type="date" value={orderDate} onChange={(e) => setOrderDate(e.target.value)} /></div>
            <div className="field"><label>預進貨日期</label><input type="date" value={arrivalDate} onChange={(e) => setArrivalDate(e.target.value)} /></div>
            <div className="field"><label>預進貨數量</label><input type="number" min="0" step="0.01" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
          </div>
          <div className="toolbar" style={{ marginTop: 16, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose}>取消</button>
            <button type="submit" className="primary">登記</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ConfirmArrivalModal({ pending, onClose, onDone, setError }) {
  const [receivedQty, setReceivedQty] = useState(pending.expected_qty)

  async function submit(e) {
    e.preventDefault()
    try {
      await api.post(`/procurement/pending/${pending.pending_id}/confirm-arrival`, { received_qty: Number(receivedQty) })
      onDone()
    } catch (e) {
      setError(e.message)
    }
  }

  const shortfall = Number(pending.expected_qty) - Number(receivedQty || 0)

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">確認到貨 — {pending.product_id}</div>
        <p className="page-desc">預進貨量 {pending.expected_qty},支援部分到貨:若實際到貨量不足,系統將自動以剩餘量產生一筆新的待到貨紀錄。</p>
        <form onSubmit={submit}>
          <div className="field">
            <label>實際到貨數量</label>
            <input type="number" min="0" step="0.01" value={receivedQty} onChange={(e) => setReceivedQty(e.target.value)} />
          </div>
          {shortfall > 0 && <div className="alert info" style={{ marginTop: 10 }}>將自動產生剩餘量 {shortfall} 的新待到貨紀錄。</div>}
          <div className="toolbar" style={{ marginTop: 16, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose}>取消</button>
            <button type="submit" className="primary">確認到貨</button>
          </div>
        </form>
      </div>
    </div>
  )
}
