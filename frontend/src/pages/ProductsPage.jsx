import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

const EMPTY_FORM = {
  product_id: '',
  product_name: '',
  unit: '',
  category: '',
  is_composite: false,
  stock_nature: 'normal',
  stock_planning: 'active',
  lead_time_days: 0,
  lead_time_type: 'procurement',
  safety_stock_qty: 0,
  supplier_id: '',
  processing_plant_id: '',
  status: 'active',
}

export default function ProductsPage() {
  const [products, setProducts] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [plants, setPlants] = useState([])
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [natureFilter, setNatureFilter] = useState('')
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [importMode, setImportMode] = useState('create')
  const [importFile, setImportFile] = useState(null)
  const [importResult, setImportResult] = useState(null)
  const [importing, setImporting] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (statusFilter) params.set('status', statusFilter)
      if (natureFilter) params.set('stock_nature', natureFilter)
      const [productsData, supplierData, plantData] = await Promise.all([
        api.get(`/products?${params.toString()}`),
        api.get('/suppliers'),
        api.get('/plants'),
      ])
      setProducts(productsData)
      setSuppliers(supplierData)
      setPlants(plantData)
    } catch (e) {
      setError(e.message)
    }
  }, [q, statusFilter, natureFilter])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    setForm(EMPTY_FORM)
    setEditingId(null)
    setShowForm(true)
  }

  function openEdit(p) {
    setForm({
      product_id: p.product_id,
      product_name: p.product_name,
      unit: p.unit,
      category: p.category,
      is_composite: p.is_composite,
      stock_nature: p.stock_nature,
      stock_planning: p.stock_planning,
      lead_time_days: p.lead_time_days,
      lead_time_type: p.lead_time_type,
      safety_stock_qty: p.safety_stock_qty,
      supplier_id: p.supplier_id || '',
      processing_plant_id: p.processing_plant_id || '',
      status: p.status,
    })
    setEditingId(p.product_id)
    setShowForm(true)
  }

  async function submitForm(e) {
    e.preventDefault()
    setError('')
    const payload = {
      ...form,
      lead_time_days: Number(form.lead_time_days),
      safety_stock_qty: Number(form.safety_stock_qty),
      supplier_id: form.supplier_id || null,
      processing_plant_id: form.processing_plant_id || null,
    }
    try {
      if (editingId) {
        const { product_id, ...body } = payload
        await api.put(`/products/${editingId}`, body)
      } else {
        await api.post('/products', payload)
      }
      setShowForm(false)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function toggleStockPlanning(p) {
    const next = p.stock_planning === 'active' ? 'manual' : 'active'
    try {
      await api.patch(`/products/${p.product_id}/stock-planning?stock_planning=${next}`)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function submitImport(e) {
    e.preventDefault()
    if (!importFile) return
    setImporting(true)
    setImportResult(null)
    setError('')
    try {
      const fd = new FormData()
      fd.append('mode', importMode)
      fd.append('file', importFile)
      const result = await api.upload('/products/import', fd)
      setImportResult(result)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>商品管理</h1>
          <p className="page-desc">商品主檔清單、需備庫狀態切換、前置時間與安全庫存維護。</p>
        </div>
        <button className="primary" onClick={openCreate}>+ 新增商品</button>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="panel">
        <div className="toolbar">
          <input placeholder="搜尋商品編號/名稱" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">全部狀態</option>
            <option value="active">啟用</option>
            <option value="inactive">停用</option>
          </select>
          <select value={natureFilter} onChange={(e) => setNatureFilter(e.target.value)}>
            <option value="">全部庫存性質</option>
            <option value="normal">一般庫存</option>
            <option value="non_stock">非庫存項目</option>
          </select>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>商品編號</th>
                <th>商品名稱</th>
                <th>單位</th>
                <th>分類</th>
                <th>庫存性質</th>
                <th>備庫規劃</th>
                <th>前置時間</th>
                <th>安全庫存</th>
                <th>狀態</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.product_id}>
                  <td>{p.product_id}</td>
                  <td>{p.product_name}{p.is_composite ? <span className="badge neutral" style={{ marginLeft: 6 }}>組合/加工品</span> : null}</td>
                  <td>{p.unit}</td>
                  <td>{p.category}</td>
                  <td>{p.stock_nature === 'normal' ? '一般庫存' : <span className="badge neutral">非庫存</span>}</td>
                  <td>
                    {p.stock_nature === 'normal' ? (
                      <button onClick={() => toggleStockPlanning(p)}>
                        {p.stock_planning === 'active' ? <span className="badge ok">主動備庫</span> : <span className="badge warn">人工判斷</span>}
                      </button>
                    ) : <span className="muted">—</span>}
                  </td>
                  <td>{p.lead_time_days} 天({typeLabel(p.lead_time_type)})</td>
                  <td>{p.safety_stock_qty}</td>
                  <td>{p.status === 'active' ? <span className="badge ok">啟用</span> : <span className="badge neutral">停用</span>}</td>
                  <td><button onClick={() => openEdit(p)}>編輯</button></td>
                </tr>
              ))}
              {products.length === 0 && (
                <tr><td colSpan={10} className="empty-state">尚無商品資料</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">批次匯入</div>
        <div className="tabs">
          <div className={'tab' + (importMode === 'create' ? ' active' : '')} onClick={() => setImportMode('create')}>新增</div>
          <div className={'tab' + (importMode === 'update' ? ' active' : '')} onClick={() => setImportMode('update')}>更新既有資料</div>
        </div>
        <p className="page-desc">
          {importMode === 'create'
            ? '新增介面:商品編號若已存在則該列視為錯誤,不會覆蓋既有資料。'
            : '更新介面:商品編號若不存在則該列視為錯誤。BOM 匯出檔不含前置時間,請確認 lead_time_days / lead_time_type 欄位已填寫。'}
        </p>
        <form onSubmit={submitImport} className="toolbar">
          <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setImportFile(e.target.files[0])} />
          <button className="primary" type="submit" disabled={importing || !importFile}>
            {importing ? '匯入中…' : '開始匯入'}
          </button>
        </form>
        {importResult && (
          <div className={'alert ' + (importResult.error_count > 0 ? 'error' : 'success')}>
            成功 {importResult.success_count} 筆,錯誤 {importResult.error_count} 筆。
            {importResult.error_detail && (
              <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{JSON.stringify(JSON.parse(importResult.error_detail), null, 2)}</pre>
            )}
          </div>
        )}
      </div>

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="panel-title">{editingId ? `編輯商品 ${editingId}` : '新增商品'}</div>
            <form onSubmit={submitForm}>
              <div className="form-grid">
                {!editingId && (
                  <div className="field">
                    <label>商品編號(ERP SKU)</label>
                    <input required value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} />
                  </div>
                )}
                <div className="field">
                  <label>商品名稱</label>
                  <input required value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
                </div>
                <div className="field">
                  <label>單位</label>
                  <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
                </div>
                <div className="field">
                  <label>分類</label>
                  <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
                </div>
                <div className="field">
                  <label>是否為組合品/加工品</label>
                  <select value={form.is_composite ? '1' : '0'} onChange={(e) => setForm({ ...form, is_composite: e.target.value === '1' })}>
                    <option value="0">否</option>
                    <option value="1">是(需 BOM 展開)</option>
                  </select>
                </div>
                <div className="field">
                  <label>庫存性質</label>
                  <select value={form.stock_nature} onChange={(e) => setForm({ ...form, stock_nature: e.target.value })}>
                    <option value="normal">一般庫存商品</option>
                    <option value="non_stock">非庫存項目(服務/贈品)</option>
                  </select>
                </div>
                <div className="field">
                  <label>備庫規劃</label>
                  <select value={form.stock_planning} onChange={(e) => setForm({ ...form, stock_planning: e.target.value })}>
                    <option value="active">主動備庫</option>
                    <option value="manual">人工判斷(一次性/業務需求)</option>
                  </select>
                </div>
                <div className="field">
                  <label>前置時間天數</label>
                  <input type="number" min="0" value={form.lead_time_days} onChange={(e) => setForm({ ...form, lead_time_days: e.target.value })} />
                </div>
                <div className="field">
                  <label>前置時間性質</label>
                  <select value={form.lead_time_type} onChange={(e) => setForm({ ...form, lead_time_type: e.target.value })}>
                    <option value="procurement">採購(原料外購)</option>
                    <option value="processing">加工充填</option>
                    <option value="qc">檢驗放行(QC)</option>
                  </select>
                </div>
                <div className="field">
                  <label>安全庫存量</label>
                  <input type="number" min="0" step="0.01" value={form.safety_stock_qty} onChange={(e) => setForm({ ...form, safety_stock_qty: e.target.value })} />
                </div>
                <div className="field">
                  <label>供應商(採購類)</label>
                  <select value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
                    <option value="">—</option>
                    {suppliers.map((s) => <option key={s.supplier_id} value={s.supplier_id}>{s.supplier_name}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label>加工廠(加工/組裝類)</label>
                  <select value={form.processing_plant_id} onChange={(e) => setForm({ ...form, processing_plant_id: e.target.value })}>
                    <option value="">—</option>
                    {plants.map((pl) => <option key={pl.plant_id} value={pl.plant_id}>{pl.plant_name}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label>狀態</label>
                  <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                    <option value="active">啟用</option>
                    <option value="inactive">停用</option>
                  </select>
                </div>
              </div>
              <div className="toolbar" style={{ marginTop: 16, justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setShowForm(false)}>取消</button>
                <button type="submit" className="primary">儲存</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function typeLabel(t) {
  return { procurement: '採購', processing: '加工充填', qc: 'QC放行' }[t] || t
}
