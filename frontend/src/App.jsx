import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { UserProvider } from './context/UserContext'
import Layout from './components/Layout'
import ProductsPage from './pages/ProductsPage'
import BomPage from './pages/BomPage'
import SuppliersPage from './pages/SuppliersPage'
import ChannelsPage from './pages/ChannelsPage'
import ImportCenterPage from './pages/ImportCenterPage'
import DashboardPage from './pages/DashboardPage'
import GapTracePage from './pages/GapTracePage'
import ProcurementPage from './pages/ProcurementPage'
import IgnoreReviewPage from './pages/IgnoreReviewPage'
import DistributionPage from './pages/DistributionPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/bom" element={<BomPage />} />
            <Route path="/suppliers" element={<SuppliersPage />} />
            <Route path="/channels" element={<ChannelsPage />} />
            <Route path="/import-center" element={<ImportCenterPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/gap-trace" element={<GapTracePage />} />
            <Route path="/procurement" element={<ProcurementPage />} />
            <Route path="/ignore-review" element={<IgnoreReviewPage />} />
            <Route path="/distribution" element={<DistributionPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}
