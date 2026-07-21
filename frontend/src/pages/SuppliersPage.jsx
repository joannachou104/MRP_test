import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([])
  const [error, setError] = useState('')
  const [form, setForm] = useState({ supplier_id: '', supplier_name: '', min_order_qty: '' })
  const [editingId, setEditingId] = useState(null)

  const load = useCallback(async () => {
    setError('')
    try {
      setSuppliers(await api.get('/suppliers'))
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function edit(s) {
    setEditingId(s.supplier_id)
    setForm({ supplier_id: s.supplier_id, supplier_name: s.supplier_name, min_order_qty: s.min_order_qty ?? '' })
  }

  function resetForm() {
    setEditingId(null)
    setForm({ supplier_id: '', supplier_name: '', min_order_qty: '' })
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      const payload = { supplier_name: form.supplier_name, min_order_qty: form.min_order_qty === '' ? null : Number(form.min_order_qty) }
      if (editingId) {
        await api.put(`/suppliers/${editingId}`, payload)
      } else {
        await api.post('/suppliers', { ...payload, supplier_id: form.supplier_id })
      }
      resetForm()
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function remove(id) {
    if (!confirm(`確定刪除供應商 ${id}?`)) return
    try {
      await api.del(`/suppliers/${id}`)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>供應商設定</h1>
          <p className="page-desc">供應商主檔、最小採購量維護。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="panel">
        <div className="panel-title">{editingId ? `編輯供應商 ${editingId}` : '新增供應商'}</div>
        <form onSubmit={submit} className="toolbar">
          {!editingId && (
            <input required placeholder="供應商編號" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} />
          )}
          <input required placeholder="供應商名稱" value={form.supplier_name} onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} />
          <input type="number" min="0" placeholder="最小採購量(選填)" value={form.min_order_qty} onChange={(e) => setForm({ ...form, min_order_qty: e.target.value })} />
          <button className="primary" type="submit">儲存</button>
          {editingId && <button type="button" onClick={resetForm}>取消編輯</button>}
        </form>
      </div>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>供應商編號</th><th>供應商名稱</th><th>最小採購量</th><th></th></tr></thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.supplier_id}>
                  <td>{s.supplier_id}</td>
                  <td>{s.supplier_name}</td>
                  <td>{s.min_order_qty ?? '—'}</td>
                  <td>
                    <button onClick={() => edit(s)}>編輯</button>{' '}
                    <button className="danger" onClick={() => remove(s.supplier_id)}>刪除</button>
                  </td>
                </tr>
              ))}
              {suppliers.length === 0 && <tr><td colSpan={4} className="empty-state">尚無供應商資料</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
