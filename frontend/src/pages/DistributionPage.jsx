import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

const SECTIONS = [
  { key: 'plants', label: '加工廠/包裝廠主檔' },
  { key: 'orders', label: '委外加工排程匯入' },
  { key: 'generate', label: '配送清單產生' },
  { key: 'history', label: '配送批次歷史' },
]

export default function DistributionPage() {
  const [section, setSection] = useState('generate')

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>加工配送管理</h1>
          <p className="page-desc">加工廠/包裝廠主檔、委外加工排程匯入(ERP)、原料/成品配送清單產生。</p>
        </div>
      </div>
      <div className="tabs">
        {SECTIONS.map((s) => (
          <div key={s.key} className={'tab' + (section === s.key ? ' active' : '')} onClick={() => setSection(s.key)}>{s.label}</div>
        ))}
      </div>
      {section === 'plants' && <PlantsSection />}
      {section === 'orders' && <OrdersSection />}
      {section === 'generate' && <GenerateSection />}
      {section === 'history' && <HistorySection />}
    </div>
  )
}

function PlantsSection() {
  const [plants, setPlants] = useState([])
  const [form, setForm] = useState({ plant_id: '', plant_name: '', contact_info: '' })
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setPlants(await api.get('/plants')) } catch (e) { setError(e.message) }
  }, [])
  useEffect(() => { load() }, [load])

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/plants', form)
      setForm({ plant_id: '', plant_name: '', contact_info: '' })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function toggleStatus(p) {
    try {
      await api.put(`/plants/${p.plant_id}`, { status: p.status === 'active' ? 'inactive' : 'active' })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="panel">
      {error && <div className="alert error">{error}</div>}
      <div className="panel-title">新增加工廠/包裝廠</div>
      <form onSubmit={submit} className="toolbar">
        <input required placeholder="編號" value={form.plant_id} onChange={(e) => setForm({ ...form, plant_id: e.target.value })} />
        <input required placeholder="名稱" value={form.plant_name} onChange={(e) => setForm({ ...form, plant_name: e.target.value })} />
        <input placeholder="聯絡資訊(選填)" value={form.contact_info} onChange={(e) => setForm({ ...form, contact_info: e.target.value })} />
        <button className="primary" type="submit">新增</button>
      </form>
      <div className="table-wrap" style={{ marginTop: 12 }}>
        <table>
          <thead><tr><th>編號</th><th>名稱</th><th>聯絡資訊</th><th>狀態</th><th></th></tr></thead>
          <tbody>
            {plants.map((p) => (
              <tr key={p.plant_id}>
                <td>{p.plant_id}</td><td>{p.plant_name}</td><td>{p.contact_info || '—'}</td>
                <td>{p.status === 'active' ? <span className="badge ok">啟用</span> : <span className="badge neutral">停用</span>}</td>
                <td><button onClick={() => toggleStatus(p)}>切換狀態</button></td>
              </tr>
            ))}
            {plants.length === 0 && <tr><td colSpan={5} className="empty-state">尚無加工廠資料</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function OrdersSection() {
  const [orders, setOrders] = useState([])
  const [products, setProducts] = useState([])
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const [o, p] = await Promise.all([api.get('/processing-orders'), api.get('/products')])
      setOrders(o)
      setProducts(p)
    } catch (e) { setError(e.message) }
  }, [])
  useEffect(() => { load() }, [load])

  async function submit(e) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      setResult(await api.upload('/processing-orders/import', fd))
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  function productName(id) { return products.find((p) => p.product_id === id)?.product_name || id }

  return (
    <div className="panel">
      {error && <div className="alert error">{error}</div>}
      <div className="panel-title">委外加工排程匯入(ERP 委外加工明細)</div>
      <p className="page-desc">生產排程完全來自 ERP 匯入,系統不自動產生排程建議。欄位:product_id、plant_id、planned_qty、required_date。</p>
      <form onSubmit={submit} className="toolbar">
        <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files[0])} />
        <button className="primary" type="submit" disabled={busy || !file}>{busy ? '匯入中…' : '開始匯入'}</button>
      </form>
      {result && (
        <div className={'alert ' + (result.error_count > 0 ? 'error' : 'success')}>
          成功 {result.success_count} 筆,錯誤 {result.error_count} 筆。
          {result.errors?.length > 0 && <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(result.errors, null, 2)}</pre>}
        </div>
      )}
      <div className="table-wrap" style={{ marginTop: 12 }}>
        <table>
          <thead><tr><th>成品</th><th>加工廠</th><th>計畫生產量</th><th>需求日期</th></tr></thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.order_id}>
                <td>{o.product_id} - {productName(o.product_id)}</td>
                <td>{o.plant_id}</td>
                <td>{o.planned_qty}</td>
                <td>{o.required_date}</td>
              </tr>
            ))}
            {orders.length === 0 && <tr><td colSpan={4} className="empty-state">尚無委外加工排程</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function GenerateSection() {
  const [products, setProducts] = useState([])
  const [materialId, setMaterialId] = useState('')
  const [totalQty, setTotalQty] = useState('')
  const [sourceType, setSourceType] = useState('inventory_transfer')
  const [sourceRef, setSourceRef] = useState('')
  const [stockHint, setStockHint] = useState(null)
  const [batch, setBatch] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/products').then(setProducts).catch((e) => setError(e.message))
  }, [])

  const selectedProduct = products.find((p) => p.product_id === materialId)
  const isFinishedGoodToCombo = selectedProduct?.is_composite

  useEffect(() => {
    setStockHint(null)
    if (materialId) {
      api.get(`/distribution/stock-hint/${materialId}`).then((r) => setStockHint(r.current_stock)).catch(() => {})
    }
  }, [materialId])

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = await api.post('/distribution/generate', {
        material_product_id: materialId,
        total_available_qty: Number(totalQty),
        source_type: sourceType,
        source_reference: sourceRef || null,
      })
      setBatch(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      {error && <div className="alert error">{error}</div>}
      <div className="panel-title">配送清單產生</div>
      <p className="page-desc">
        輸入下層節點商品(原料或成品)、本次可分配總量、來源類型,系統依 BOM 展開與委外加工排程,依交期優先順序自動分配給各廠。
      </p>
      <form onSubmit={submit} className="form-grid">
        <div className="field">
          <label>下層節點商品(原料/成品)</label>
          <select required value={materialId} onChange={(e) => setMaterialId(e.target.value)}>
            <option value="">選擇商品…</option>
            {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>)}
          </select>
        </div>
        <div className="field">
          <label>本次可分配總量</label>
          <input required type="number" min="0" step="0.01" value={totalQty} onChange={(e) => setTotalQty(e.target.value)} />
        </div>
        <div className="field">
          <label>來源類型</label>
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="inventory_transfer">公司庫存轉移</option>
            <option value="direct_procurement" disabled={isFinishedGoodToCombo}>
              原料商直送加工廠{isFinishedGoodToCombo ? '(成品→組合品情境不適用)' : ''}
            </option>
          </select>
        </div>
        <div className="field">
          <label>來源單號(選填)</label>
          <input value={sourceRef} onChange={(e) => setSourceRef(e.target.value)} />
        </div>
        <div className="field" style={{ alignSelf: 'end' }}>
          <button className="primary" type="submit" disabled={busy || !materialId || !totalQty}>{busy ? '產生中…' : '產生配送清單'}</button>
        </div>
      </form>
      {stockHint != null && (
        <div className="alert info">參考:該商品目前庫存(最新快照)為 {stockHint}(僅提示,不強制卡控,多段串鏈第二段可據此判斷是否已生產出來)。</div>
      )}

      {batch && <BatchDetail batch={batch} onUpdated={setBatch} setError={setError} />}
    </div>
  )
}

function HistorySection() {
  const [batches, setBatches] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setBatches(await api.get('/distribution')) } catch (e) { setError(e.message) }
  }, [])
  useEffect(() => { load() }, [load])

  function updateOne(updated) {
    setBatches((prev) => prev.map((b) => (b.batch_id === updated.batch_id ? updated : b)))
  }

  return (
    <div>
      {error && <div className="alert error">{error}</div>}
      {batches.map((b) => <BatchDetail key={b.batch_id} batch={b} onUpdated={updateOne} setError={setError} />)}
      {batches.length === 0 && <div className="panel empty-state">尚無配送批次紀錄</div>}
    </div>
  )
}

function BatchDetail({ batch, onUpdated, setError }) {
  const [confirming, setConfirming] = useState(false)

  async function confirmDisposition(disposition) {
    setError('')
    try {
      const updated = await api.post(`/distribution/${batch.batch_id}/confirm-disposition`, { disposition })
      onUpdated(updated)
      setConfirming(false)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">配送批次 {batch.batch_id}</div>
      <div className="form-grid">
        <div className="field"><label>下層節點商品</label><div>{batch.material_product_id}</div></div>
        <div className="field"><label>來源類型</label><div>{batch.source_type === 'inventory_transfer' ? '庫存轉移' : '原料商直送'}</div></div>
        <div className="field"><label>可分配總量</label><div>{batch.total_available_qty}</div></div>
        <div className="field"><label>剩餘量</label><div>{batch.remaining_qty}</div></div>
        <div className="field"><label>剩餘量去向</label>
          <div>
            {batch.remaining_disposition === 'unconfirmed' && batch.remaining_qty > 0 && <span className="badge warn">待確認</span>}
            {batch.remaining_disposition === 'return_to_warehouse' && <span className="badge ok">送回公司倉庫</span>}
            {batch.remaining_disposition === 'keep_at_source' && <span className="badge neutral">暫留原地</span>}
            {batch.remaining_disposition === 'unconfirmed' && batch.remaining_qty <= 0 && <span className="muted">— (無剩餘量)</span>}
          </div>
        </div>
      </div>
      {batch.remaining_qty > 0 && batch.remaining_disposition === 'unconfirmed' && (
        <div className="toolbar" style={{ marginTop: 10 }}>
          {!confirming ? (
            <button className="primary" onClick={() => setConfirming(true)}>確認剩餘量去向</button>
          ) : (
            <>
              <button onClick={() => confirmDisposition('return_to_warehouse')}>送回公司倉庫</button>
              <button onClick={() => confirmDisposition('keep_at_source')}>暫留原地</button>
              <button onClick={() => setConfirming(false)}>取消</button>
            </>
          )}
        </div>
      )}
      <div className="table-wrap" style={{ marginTop: 12 }}>
        <table>
          <thead><tr><th>優先序</th><th>對應成品</th><th>對應廠</th><th>需求量</th><th>分配量</th><th>缺口量</th></tr></thead>
          <tbody>
            {batch.details?.map((d) => (
              <tr key={d.detail_id}>
                <td>{d.priority_rank}</td>
                <td>{d.target_product_id}</td>
                <td>{d.target_plant_id}</td>
                <td>{d.required_qty}</td>
                <td>{d.allocated_qty}</td>
                <td>{d.shortage_qty > 0 ? <span className="badge danger">{d.shortage_qty}</span> : 0}</td>
              </tr>
            ))}
            {(!batch.details || batch.details.length === 0) && <tr><td colSpan={6} className="empty-state">無配送明細(可能無對應委外加工排程)</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
