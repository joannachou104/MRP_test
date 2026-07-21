import { useEffect, useState, useCallback } from 'react'
import { api } from '../api'

const SOURCE_LABEL = {
  external_quarterly: '外部季預測(大宗)',
  external_monthly: '外部月預測(飯店)',
  internal_calculated: '系統內部計算(B2C)',
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState([])
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')
  const [form, setForm] = useState({ channel_id: '', channel_name: '', forecast_source: 'external_quarterly' })

  const [forecastChannel, setForecastChannel] = useState('')
  const [forecastProduct, setForecastProduct] = useState('')
  const [forecasts, setForecasts] = useState([])

  const [b2cProduct, setB2cProduct] = useState('')
  const [b2cMonth, setB2cMonth] = useState(() => new Date().toISOString().slice(0, 7))
  const [b2cResult, setB2cResult] = useState(null)

  const load = useCallback(async () => {
    setError('')
    try {
      const [chs, prods] = await Promise.all([api.get('/channels'), api.get('/products')])
      setChannels(chs)
      setProducts(prods)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const loadForecasts = useCallback(async () => {
    const params = new URLSearchParams()
    if (forecastChannel) params.set('channel_id', forecastChannel)
    if (forecastProduct) params.set('product_id', forecastProduct)
    try {
      setForecasts(await api.get(`/channels/forecasts?${params.toString()}`))
    } catch (e) {
      setError(e.message)
    }
  }, [forecastChannel, forecastProduct])

  useEffect(() => { loadForecasts() }, [loadForecasts])

  async function submitChannel(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/channels', form)
      setForm({ channel_id: '', channel_name: '', forecast_source: 'external_quarterly' })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function runB2cCalc() {
    if (!b2cProduct) return
    setError('')
    try {
      setB2cResult(await api.get(`/channels/b2c-calc/${b2cProduct}?year_month=${b2cMonth}`))
    } catch (e) {
      setError(e.message)
    }
  }

  function productName(id) {
    return products.find((p) => p.product_id === id)?.product_name || id
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>通路管理</h1>
          <p className="page-desc">通路主檔維護、預測資料查詢、B2C 計算結果查核。預測上傳請至「資料匯入中心」。</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="panel">
        <div className="panel-title">新增通路</div>
        <form onSubmit={submitChannel} className="toolbar">
          <input required placeholder="通路編號" value={form.channel_id} onChange={(e) => setForm({ ...form, channel_id: e.target.value })} />
          <input required placeholder="通路名稱" value={form.channel_name} onChange={(e) => setForm({ ...form, channel_name: e.target.value })} />
          <select value={form.forecast_source} onChange={(e) => setForm({ ...form, forecast_source: e.target.value })}>
            <option value="external_quarterly">外部季預測(大宗,按50/30/20拆分)</option>
            <option value="external_monthly">外部月預測(飯店)</option>
            <option value="internal_calculated">系統內部計算(B2C)</option>
          </select>
          <button className="primary" type="submit">新增</button>
        </form>
      </div>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>通路編號</th><th>通路名稱</th><th>預測來源</th></tr></thead>
            <tbody>
              {channels.map((c) => (
                <tr key={c.channel_id}>
                  <td>{c.channel_id}</td>
                  <td>{c.channel_name}</td>
                  <td>{SOURCE_LABEL[c.forecast_source] || c.forecast_source}</td>
                </tr>
              ))}
              {channels.length === 0 && <tr><td colSpan={3} className="empty-state">尚無通路資料</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">大宗/飯店預測資料查詢</div>
        <div className="toolbar">
          <select value={forecastChannel} onChange={(e) => setForecastChannel(e.target.value)}>
            <option value="">全部通路</option>
            {channels.filter((c) => c.forecast_source !== 'internal_calculated').map((c) => (
              <option key={c.channel_id} value={c.channel_id}>{c.channel_name}</option>
            ))}
          </select>
          <select value={forecastProduct} onChange={(e) => setForecastProduct(e.target.value)}>
            <option value="">全部商品</option>
            {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>)}
          </select>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>通路</th><th>商品</th><th>週期類型</th><th>期間</th><th>預測量</th></tr></thead>
            <tbody>
              {forecasts.map((f) => (
                <tr key={f.forecast_id}>
                  <td>{f.channel_id}</td>
                  <td>{productName(f.product_id)}</td>
                  <td>{f.period_type === 'quarter' ? '季' : '月'}</td>
                  <td>{f.period_value}</td>
                  <td>{f.forecast_qty}</td>
                </tr>
              ))}
              {forecasts.length === 0 && <tr><td colSpan={5} className="empty-state">尚無預測資料</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">B2C 計算結果查詢</div>
        <p className="page-desc">近3個月銷量平均 x (1 + 去年同期YOY成長率),YOY 上限 ±50%。</p>
        <div className="toolbar">
          <select value={b2cProduct} onChange={(e) => setB2cProduct(e.target.value)}>
            <option value="">選擇商品…</option>
            {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_id} - {p.product_name}</option>)}
          </select>
          <input type="month" value={b2cMonth} onChange={(e) => setB2cMonth(e.target.value)} />
          <button className="primary" onClick={runB2cCalc}>查詢</button>
        </div>
        {b2cResult && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>通路</th><th>B2C 計算預測量</th></tr></thead>
              <tbody>
                {b2cResult.map((r) => (
                  <tr key={r.channel_id}><td>{r.channel_name}</td><td>{r.b2c_forecast_qty.toFixed(2)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
