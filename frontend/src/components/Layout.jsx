import { NavLink, Outlet } from 'react-router-dom'
import { useUser } from '../context/UserContext'

const NAV_GROUPS = [
  {
    title: '主檔管理',
    items: [
      { to: '/products', label: '商品管理' },
      { to: '/bom', label: 'BOM 管理' },
      { to: '/suppliers', label: '供應商設定' },
      { to: '/channels', label: '通路管理' },
    ],
  },
  {
    title: '資料匯入',
    items: [{ to: '/import-center', label: '資料匯入中心' }],
  },
  {
    title: 'MRP 運算',
    items: [
      { to: '/dashboard', label: 'MRP 運算儀表板' },
      { to: '/gap-trace', label: '缺口追溯' },
      { to: '/procurement', label: '採購建議' },
      { to: '/ignore-review', label: '忽略清單複核' },
    ],
  },
  {
    title: '加工配送',
    items: [{ to: '/distribution', label: '加工配送管理' }],
  },
  {
    title: '系統',
    items: [{ to: '/settings', label: '系統設定/權限' }],
  },
]

export default function Layout() {
  const { user, changeUser, presetUsers } = useUser()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">客製化 MRP 系統<span className="brand-tag">本機測試版</span></div>
        <nav>
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.title}>
              <div className="nav-group-title">{group.title}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <div className="main-col">
        <header className="topbar">
          <div className="topbar-title">洗沐保養品 MRP 測試環境</div>
          <div className="role-switcher">
            <label>目前操作角色:</label>
            <select
              value={user.role}
              onChange={(e) => {
                const preset = presetUsers.find((p) => p.role === e.target.value)
                changeUser(preset)
              }}
            >
              {presetUsers.map((p) => (
                <option key={p.role} value={p.role}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
