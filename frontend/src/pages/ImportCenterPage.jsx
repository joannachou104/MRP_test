import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

const SECTIONS = [
  { key: 'sales', label: '銷貨/銷退交易上傳' },
  { key: 'inventory', label: '每日庫存上傳' },
  { key: 'forecast', label: '通路預測上傳' },
  { key: 'history', label: '匯入歷史與錯誤紀錄' },
]

export default function ImportCenterPage() {
  const [section, setSection] = useState('sales')

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>資料匯入中心</h1>
          <p className="page-desc">銷貨/銷退交易上傳(首次全量+每日增量)、每日庫存上傳、通路預測上傳,以及匯入歷史與錯誤紀錄。</p>
        </div>
      </div>
      <div className="tabs">
        {SECTIONS.map((s) => (
          <div key={s.key} className={'tab' + (section === s.key ? ' active' : '')} onClick={() => setSection(s.key)}>
            {s.label}
          </div>
        ))}
      </div>
      {section === 'sales' && <SalesImportSection />}
      {section === 'inventory' && <InventoryImportSection />}
      {section === 'forecast' && <ForecastImportSection />}
      {section === 'history' && <ImportHistorySection />}
    </div>
  )
}

function SalesImportSection() {
  const [uploadType, setUploadType] = useState('bulk_initial')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('upload_type', uploadType)
      fd.append('file', file)
      setResult(await api.upload('/sales/import', fd))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">銷貨/銷退交易上傳</div>
      <p className="page-desc">持續累積交易表:首次上傳歷史全量資料,之後每日上傳前一日資料。用於計算 B2C 近3個月移動平均與 YOY 成長率。</p>
      {error && <div className="alert error">{error}</div>}
      <div className="toolbar">
        <select value={uploadType} onChange={(e) => setUploadType(e.target.value)}>
          <option value="bulk_initial">首次全量歷史上傳</option>
          <option value="daily_incremental">每日增量上傳(前一日資料)</option>
        </select>
      </div>
      <form onSubmit={submit} className="toolbar">
        <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files[0])} />
        <button className="primary" type="submit" disabled={busy || !file}>{busy ? '匯入中…' : '開始匯入'}</button>
      </form>
      <p className="muted">欄位:doc_no(選填)、doc_date、product_id、channel_id、quantity、doc_type(sale/return)</p>
      {result && <ImportResultBlock result={result} />}
    </div>
  )
}

function InventoryImportSection() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      setResult(await api.upload('/inventory/import', fd))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">每日庫存上傳(單一介面)</div>
      <p className="page-desc">
        欄位僅 product_id、quantity 為必填。snapshot_date 不開放人工填寫,完全由系統依伺服器時間(台灣時區)自動帶入。
        當天第一次上傳視為建立完整快照基準(active+normal 商品未列出者一律補 0);當天第二次以後上傳僅覆蓋檔案中有列出的品項。
      </p>
      {error && <div className="alert error">{error}</div>}
      <form onSubmit={submit} className="toolbar">
        <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files[0])} />
        <button className="primary" type="submit" disabled={busy || !file}>{busy ? '匯入中…' : '開始匯入'}</button>
      </form>
      {result && (
        <div>
          <div className="alert info">{result.message}{result.is_first_upload_of_day ? '(本次為當天第一次上傳,已套用整批基準補0)' : '(本次為當天補充更新,僅覆蓋檔案內品項)'}</div>
          <ImportResultBlock result={result.log} />
        </div>
      )}
    </div>
  )
}

function ForecastImportSection() {
  const [mode, setMode] = useState('create')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('mode', mode)
      fd.append('file', file)
      setResult(await api.upload('/channels/forecasts/import', fd))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">通路預測上傳</div>
      <p className="page-desc">
        欄位:channel_id、product_id、period_type(quarter/month)、period_value(如 2026-Q3 或 2026-07)、forecast_qty。
        大宗通路提供季預測,系統自動依 50/30/20 拆分至該季三個月;飯店通路直接提供月預測。
      </p>
      <div className="tabs">
        <div className={'tab' + (mode === 'create' ? ' active' : '')} onClick={() => setMode('create')}>新增</div>
        <div className={'tab' + (mode === 'update' ? ' active' : '')} onClick={() => setMode('update')}>更新既有資料</div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <form onSubmit={submit} className="toolbar">
        <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files[0])} />
        <button className="primary" type="submit" disabled={busy || !file}>{busy ? '匯入中…' : '開始匯入'}</button>
      </form>
      {result && <ImportResultBlock result={result} />}
    </div>
  )
}

function ImportHistorySection() {
  const [logs, setLogs] = useState([])
  const [typeFilter, setTypeFilter] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (typeFilter) params.set('import_type', typeFilter)
      setLogs(await api.get(`/import-logs?${params.toString()}`))
    } catch (e) {
      setError(e.message)
    }
  }, [typeFilter])

  useEffect(() => { load() }, [load])

  return (
    <div className="panel">
      <div className="panel-title">匯入歷史與錯誤紀錄</div>
      {error && <div className="alert error">{error}</div>}
      <div className="toolbar">
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">全部類型</option>
          <option value="product">商品</option>
          <option value="bom">BOM</option>
          <option value="sales_bulk">銷貨(首次全量)</option>
          <option value="sales_daily_incremental">銷貨(每日增量)</option>
          <option value="inventory_daily">每日庫存</option>
          <option value="channel_forecast">通路預測</option>
          <option value="processing_order">委外加工排程</option>
        </select>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>批次號</th><th>類型</th><th>檔名</th><th>匯入人</th><th>時間</th><th>成功</th><th>錯誤</th><th>錯誤明細</th></tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.batch_id}>
                <td>{l.batch_id}</td>
                <td>{l.import_type}</td>
                <td>{l.file_name}</td>
                <td>{l.imported_by}</td>
                <td>{new Date(l.imported_at).toLocaleString('zh-TW')}</td>
                <td>{l.success_count}</td>
                <td>{l.error_count > 0 ? <span className="badge danger">{l.error_count}</span> : 0}</td>
                <td>
                  {l.error_detail && (
                    <details>
                      <summary>查看</summary>
                      <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(JSON.parse(l.error_detail), null, 2)}</pre>
                    </details>
                  )}
                </td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={8} className="empty-state">尚無匯入紀錄</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ImportResultBlock({ result }) {
  if (!result) return null
  return (
    <div className={'alert ' + (result.error_count > 0 ? 'error' : 'success')}>
      成功 {result.success_count} 筆,錯誤 {result.error_count} 筆。
      {result.error_detail && (
        <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{JSON.stringify(JSON.parse(result.error_detail), null, 2)}</pre>
      )}
    </div>
  )
}
