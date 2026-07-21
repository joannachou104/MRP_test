import { useEffect, useState } from 'react'
import { api } from '../api'

const TRIGGER_LABEL = {
  lead_time_breach: '前置時間不足',
  below_safety_stock: '低於安全庫存',
  both: '前置時間不足 + 低於安全庫存',
}

export default function GapTracePage() {
  const [products, setProducts] = useState([])
  const [selected, setSelected] = useState('')
  const [tree, setTree] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/products').then(setProducts).catch((e) => setError(e.message))
  }, [])

  async function trace() {
    if (!selected) return
    setError('')
    try {
      setTree(await api.get(`/mrp/gap-trace/${selected}`))
    } catch (e) {
      setError(e.message)
      setTree(null)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>缺口追溯</h1>
          <p className="page-desc">選定一個缺貨商品,沿 BOM 逐層往下檢視所依賴的成品、原料各自的缺口狀態與觸發原因。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            <option value="">選擇商品…</option>
            {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>)}
          </select>
          <button className="primary" onClick={trace}>追溯</button>
        </div>
        {tree && <GapNode node={tree} />}
        {!tree && <div className="empty-state">請選擇商品後點選「追溯」</div>}
      </div>
    </div>
  )
}

function GapNode({ node }) {
  const r = node.mrp_result
  return (
    <div className="tree-node" style={{ marginLeft: node.level === 0 ? 0 : undefined, borderLeft: node.level === 0 ? 'none' : undefined, paddingLeft: node.level === 0 ? 0 : undefined }}>
      <div className="panel" style={{ marginBottom: 10 }}>
        <div className="tree-node-header">
          <strong>{node.product_id}</strong>
          <span>{node.product_name}</span>
          {node.level > 0 && <span className="muted">用量係數 x{node.total_multiplier}</span>}
          <span className="badge neutral">前置 {node.lead_time_days} 天</span>
          {r?.trigger_reason && <span className="badge warn">{TRIGGER_LABEL[r.trigger_reason]}</span>}
          {!r?.trigger_reason && r && <span className="badge ok">正常</span>}
          {!r && <span className="badge neutral">尚無運算結果</span>}
        </div>
        {r && (
          <div className="form-grid" style={{ marginTop: 8 }}>
            <Stat label="運算日期" value={r.run_date} />
            <Stat label="預測需求" value={r.forecast_demand} />
            <Stat label="目前庫存" value={r.current_stock} />
            <Stat label="可銷售天數" value={r.sellable_days?.toFixed?.(2)} />
            <Stat label="淨需求" value={r.net_requirement} />
            <Stat label="建議採購量" value={r.suggested_order_qty} />
            <Stat label="建議下單期限" value={r.suggested_order_deadline || '—'} />
          </div>
        )}
      </div>
      {node.children?.map((c) => <GapNode key={c.product_id} node={c} />)}
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="field">
      <label>{label}</label>
      <div>{value}</div>
    </div>
  )
}
