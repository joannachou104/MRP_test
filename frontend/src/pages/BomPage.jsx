import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

export default function BomPage() {
  const [products, setProducts] = useState([])
  const [bomRows, setBomRows] = useState([])
  const [parentFilter, setParentFilter] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({ parent_product_id: '', child_product_id: '', quantity_per_unit: 1 })
  const [treeRoot, setTreeRoot] = useState('')
  const [tree, setTree] = useState(null)
  const [importMode, setImportMode] = useState('create')
  const [importFile, setImportFile] = useState(null)
  const [importResult, setImportResult] = useState(null)
  const [importing, setImporting] = useState(false)

  const loadProducts = useCallback(async () => {
    setProducts(await api.get('/products'))
  }, [])

  const loadBom = useCallback(async () => {
    const params = new URLSearchParams()
    if (parentFilter) params.set('parent_product_id', parentFilter)
    setBomRows(await api.get(`/bom?${params.toString()}`))
  }, [parentFilter])

  useEffect(() => { loadProducts() }, [loadProducts])
  useEffect(() => { loadBom() }, [loadBom])

  async function addRow(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/bom', { ...form, quantity_per_unit: Number(form.quantity_per_unit) })
      setForm({ parent_product_id: '', child_product_id: '', quantity_per_unit: 1 })
      loadBom()
    } catch (e) {
      setError(e.message)
    }
  }

  async function deleteRow(bomId) {
    if (!confirm('確定刪除此 BOM 關係?')) return
    try {
      await api.del(`/bom/${bomId}`)
      loadBom()
    } catch (e) {
      setError(e.message)
    }
  }

  async function loadTree() {
    if (!treeRoot) return
    setError('')
    try {
      setTree(await api.get(`/bom/tree/${treeRoot}`))
    } catch (e) {
      setError(e.message)
      setTree(null)
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
      const result = await api.upload('/bom/import', fd)
      setImportResult(result)
      loadBom()
    } catch (e) {
      setError(e.message)
    } finally {
      setImporting(false)
    }
  }

  function productName(id) {
    return products.find((p) => p.product_id === id)?.product_name || id
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>BOM 管理</h1>
          <p className="page-desc">BOM 清單查詢、批次匯入、多層展開預覽(含各節點前置時間)。組合品(禮盒)比照此結構,成品當子項。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="panel">
        <div className="panel-title">多層展開預覽</div>
        <div className="toolbar">
          <select value={treeRoot} onChange={(e) => setTreeRoot(e.target.value)}>
            <option value="">選擇成品/組合品…</option>
            {products.filter((p) => p.is_composite).map((p) => (
              <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>
            ))}
          </select>
          <button className="primary" onClick={loadTree}>展開</button>
        </div>
        {tree && <TreeNode node={tree} />}
      </div>

      <div className="panel">
        <div className="panel-title">新增單筆 BOM 關係</div>
        <form onSubmit={addRow} className="toolbar">
          <select required value={form.parent_product_id} onChange={(e) => setForm({ ...form, parent_product_id: e.target.value })}>
            <option value="">父項(成品/組合品)</option>
            {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>)}
          </select>
          <select required value={form.child_product_id} onChange={(e) => setForm({ ...form, child_product_id: e.target.value })}>
            <option value="">子項(原料/半成品/成品)</option>
            {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>)}
          </select>
          <input type="number" step="0.0001" min="0" required placeholder="每單位用量" value={form.quantity_per_unit}
            onChange={(e) => setForm({ ...form, quantity_per_unit: e.target.value })} style={{ width: 120 }} />
          <button className="primary" type="submit">新增</button>
        </form>
      </div>

      <div className="panel">
        <div className="toolbar">
          <div className="panel-title" style={{ marginBottom: 0 }}>BOM 清單</div>
          <select value={parentFilter} onChange={(e) => setParentFilter(e.target.value)} style={{ marginLeft: 'auto' }}>
            <option value="">全部父項</option>
            {products.filter((p) => p.is_composite).map((p) => (
              <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>
            ))}
          </select>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>父項</th><th>子項</th><th>每單位用量</th><th></th></tr>
            </thead>
            <tbody>
              {bomRows.map((row) => (
                <tr key={row.bom_id}>
                  <td>{row.parent_product_id} - {productName(row.parent_product_id)}</td>
                  <td>{row.child_product_id} - {productName(row.child_product_id)}</td>
                  <td>{row.quantity_per_unit}</td>
                  <td><button className="danger" onClick={() => deleteRow(row.bom_id)}>刪除</button></td>
                </tr>
              ))}
              {bomRows.length === 0 && <tr><td colSpan={4} className="empty-state">尚無 BOM 資料</td></tr>}
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
    </div>
  )
}

function TreeNode({ node }) {
  return (
    <div className="tree-node" style={{ marginLeft: node.level === 0 ? 0 : undefined, borderLeft: node.level === 0 ? 'none' : undefined, paddingLeft: node.level === 0 ? 0 : undefined }}>
      <div className="tree-node-header">
        <strong>{node.product_id}</strong>
        <span>{node.product_name}</span>
        {node.level > 0 && <span className="muted">用量係數 x{node.total_multiplier}</span>}
        {node.lead_time_days != null && (
          <span className="badge neutral">前置 {node.lead_time_days} 天({typeLabel(node.lead_time_type)})</span>
        )}
      </div>
      {node.children?.map((c) => <TreeNode key={c.product_id} node={c} />)}
    </div>
  )
}

function typeLabel(t) {
  return { procurement: '採購', processing: '加工充填', qc: 'QC放行' }[t] || t
}
