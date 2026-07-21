import { createContext, useContext, useState, useCallback } from 'react'
import { getCurrentUser } from '../api'

const UserContext = createContext(null)

const PRESET_USERS = [
  { name: '系統管理員', role: 'admin', label: '系統管理員(admin)' },
  { name: '採購人員 Amy', role: 'procurement', label: '採購人員(procurement)' },
  { name: '唯讀訪客', role: 'viewer', label: '唯讀訪客(viewer)' },
]

export function UserProvider({ children }) {
  const [user, setUser] = useState(getCurrentUser())

  const changeUser = useCallback((next) => {
    localStorage.setItem('mrp_current_user', JSON.stringify(next))
    setUser(next)
  }, [])

  return (
    <UserContext.Provider value={{ user, changeUser, presetUsers: PRESET_USERS }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  return useContext(UserContext)
}
