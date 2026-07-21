import { useEffect, useState } from 'react'
import { api } from '../api'
import { useUser } from '../context/UserContext'

export default function SettingsPage() {
  const [users, setUsers] = useState([])
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const { presetUsers } = useUser()

  useEffect(() => {
    Promise.all([api.get('/users'), api.get('/users/change-log')])
      .then(([u, l]) => { setUsers(u); setLogs(l) })
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>系統設定/權限</h1>
          <p className="page-desc">使用者權限說明(含登記在途採購/確認到貨/標記忽略缺口操作權限)、異動紀錄查詢(交接用)。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="panel">
        <div className="panel-title">角色權限說明</div>
        <p className="page-desc">
          本機測試版採簡易角色模擬(以 HTTP Header 傳遞,非正式帳密系統),於頂部列可切換操作角色。
        </p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>角色</th><th>可執行操作</th></tr></thead>
            <tbody>
              <tr><td>admin(系統管理員)</td><td>所有操作,含登記在途採購、確認到貨、標記/取消忽略缺口</td></tr>
              <tr><td>procurement(採購人員)</td><td>登記在途採購、確認到貨、標記/取消忽略缺口</td></tr>
              <tr><td>viewer(唯讀訪客)</td><td>僅可查詢,無法執行上述操作(將收到 403 拒絕)</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">測試用使用者清單</div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>帳號</th><th>顯示名稱</th><th>角色</th></tr></thead>
            <tbody>
              {users.map((u) => <tr key={u.user_id}><td>{u.user_id}</td><td>{u.display_name}</td><td>{u.role}</td></tr>)}
              {users.length === 0 && <tr><td colSpan={3} className="empty-state">尚無使用者資料(請先執行 seed 腳本)</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">異動紀錄查詢(交接用)</div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>時間</th><th>動作</th><th>對象類型</th><th>對象</th><th>明細</th><th>操作人</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.log_id}>
                  <td>{new Date(l.operated_at).toLocaleString('zh-TW')}</td>
                  <td>{l.action_type}</td>
                  <td>{l.target_type}</td>
                  <td>{l.target_id}</td>
                  <td>{l.detail}</td>
                  <td>{l.operated_by}</td>
                </tr>
              ))}
              {logs.length === 0 && <tr><td colSpan={6} className="empty-state">尚無異動紀錄</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
