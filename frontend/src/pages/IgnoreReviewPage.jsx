import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'
import { useUser } from '../context/UserContext'

export default function IgnoreReviewPage() {
  const [list, setList] = useState([])
  const [error, setError] = useState('')
  const { user } = useUser()
  const canOperate = user.role === 'admin' || user.role === 'procurement'

  const load = useCallback(async () => {
    setError('')
    try {
      setList(await api.get('/ignore'))
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function remove(id) {
    if (!confirm('確定取消此忽略設定?該商品缺口將於下次運算重新顯示於建議清單。')) return
    try {
      await api.del(`/ignore/${id}`)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>忽略清單複核</h1>
          <p className="page-desc">列出所有目前處於忽略狀態的商品,供主管定期複核,避免問題長期擱置。缺口消失時系統會自動解除忽略。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}
      {!canOperate && <div className="alert info">目前角色為唯讀訪客,取消忽略操作將被拒絕。</div>}

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>商品編號</th><th>忽略原因</th><th>忽略人</th><th>忽略時間</th><th></th></tr></thead>
            <tbody>
              {list.map((i) => (
                <tr key={i.ignore_id}>
                  <td>{i.product_id}</td>
                  <td>{i.note || '—'}</td>
                  <td>{i.ignored_by}</td>
                  <td>{new Date(i.ignored_at).toLocaleString('zh-TW')}</td>
                  <td><button disabled={!canOperate} onClick={() => remove(i.ignore_id)}>取消忽略</button></td>
                </tr>
              ))}
              {list.length === 0 && <tr><td colSpan={5} className="empty-state">目前沒有被忽略的商品</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
