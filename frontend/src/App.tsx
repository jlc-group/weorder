import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Orders from './pages/Orders';
import OrderCreate from './pages/OrderCreate';
import OrderDetail from './pages/OrderDetail';
import Products from './pages/Products';
import PlatformBundles from './pages/PlatformBundles';
import Stock from './pages/Stock';
import StockCard from './pages/StockCard';
import Packing from './pages/Packing';
import PendingLabels from './pages/PendingLabels';
import Promotions from './pages/Promotions';
import Finance from './pages/Finance';
import FinancePerformance from './pages/FinancePerformance';
import SalesProfitability from './pages/SalesProfitability';
import OrderProfitability from './pages/OrderProfitability';
import ProfitCalculator from './pages/ProfitCalculator';
import Settings from './pages/Settings';
import InvoiceRequest from './pages/InvoiceRequest';
import InvoiceManager from './pages/InvoiceManager';
import Returns from './pages/Returns';
import DailyOutbound from './pages/DailyOutbound';
import SyncHealth from './pages/SyncHealth';
import Manifests from './pages/Manifests';
import PackingDashboard from './pages/PackingDashboard';
import SuperAdmin from './pages/SuperAdmin';
import AuthCallback from './pages/AuthCallback';
import PrintLabelsPage from './pages/PrintLabelsPage';
// Mobile Pages
import MobileMenu from './pages/mobile/MobileMenu';
import MobilePack from './pages/mobile/MobilePack';
import MobilePickList from './pages/mobile/MobilePickList';
import MobileStockCount from './pages/mobile/MobileStockCount';
import MobileReturn from './pages/mobile/MobileReturn';
import MobileSearch from './pages/mobile/MobileSearch';
import MobilePrintLabels from './pages/mobile/MobilePrintLabels';
import './App.css';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: '#f5f5f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{
            width: '40px',
            height: '40px',
            border: '4px solid #e5e7eb',
            borderTopColor: '#667eea',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <p style={{ color: '#666' }}>กำลังโหลด...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public Route - Login */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
      />

      {/* SSO Callback Route */}
      <Route path="/auth/callback" element={<AuthCallback />} />

      {/* Protected Routes */}
      <Route path="/" element={<ProtectedRoute><Navigate to="/dashboard" replace /></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />

      {/* Orders Routes */}
      <Route path="/orders" element={<ProtectedRoute><Orders /></ProtectedRoute>} />
      <Route path="/orders/create" element={<ProtectedRoute><OrderCreate /></ProtectedRoute>} />
      <Route path="/orders/:orderId" element={<ProtectedRoute><OrderDetail /></ProtectedRoute>} />
      <Route path="/products" element={<ProtectedRoute><Products /></ProtectedRoute>} />
      <Route path="/bundles" element={<ProtectedRoute><PlatformBundles /></ProtectedRoute>} />
      <Route path="/stock" element={<ProtectedRoute><Stock /></ProtectedRoute>} />
      <Route path="/stock/card/:sku" element={<ProtectedRoute><StockCard /></ProtectedRoute>} />
      <Route path="/packing" element={<ProtectedRoute><Packing /></ProtectedRoute>} />
      <Route path="/packing/dashboard" element={<ProtectedRoute><PackingDashboard /></ProtectedRoute>} />
      <Route path="/packing/print-labels" element={<ProtectedRoute><PrintLabelsPage /></ProtectedRoute>} />
      <Route path="/manifests" element={<ProtectedRoute><Manifests /></ProtectedRoute>} />
      <Route path="/pending-labels" element={<ProtectedRoute><PendingLabels /></ProtectedRoute>} />
      <Route path="/returns" element={<ProtectedRoute><Returns /></ProtectedRoute>} />
      <Route path="/promotions" element={<ProtectedRoute><Promotions /></ProtectedRoute>} />
      <Route path="/finance" element={<ProtectedRoute><Finance /></ProtectedRoute>} />
      <Route path="/finance/performance" element={<ProtectedRoute><FinancePerformance /></ProtectedRoute>} />
      <Route path="/finance/profitability" element={<ProtectedRoute><SalesProfitability /></ProtectedRoute>} />
      <Route path="/finance/order-profit" element={<ProtectedRoute><OrderProfitability /></ProtectedRoute>} />
      <Route path="/finance/calculator" element={<ProtectedRoute><ProfitCalculator /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />

      {/* Tax Invoice */}
      <Route path="/invoice-request" element={<ProtectedRoute><InvoiceRequest /></ProtectedRoute>} />
      <Route path="/invoice-manager" element={<ProtectedRoute><InvoiceManager /></ProtectedRoute>} />

      {/* Reports */}
      <Route path="/report/outbound" element={<ProtectedRoute><DailyOutbound /></ProtectedRoute>} />
      <Route path="/report/sync-health" element={<ProtectedRoute><SyncHealth /></ProtectedRoute>} />

      {/* Mobile Routes */}
      <Route path="/mobile" element={<ProtectedRoute><MobileMenu /></ProtectedRoute>} />
      <Route path="/mobile/pack" element={<ProtectedRoute><MobilePack /></ProtectedRoute>} />
      <Route path="/mobile/pick-list" element={<ProtectedRoute><MobilePickList /></ProtectedRoute>} />
      <Route path="/mobile/stock-count" element={<ProtectedRoute><MobileStockCount /></ProtectedRoute>} />
      <Route path="/mobile/return" element={<ProtectedRoute><MobileReturn /></ProtectedRoute>} />
      <Route path="/mobile/search" element={<ProtectedRoute><MobileSearch /></ProtectedRoute>} />
      <Route path="/mobile/print-labels" element={<ProtectedRoute><MobilePrintLabels /></ProtectedRoute>} />

      {/* Admin */}
      <Route path="/admin" element={<ProtectedRoute><SuperAdmin /></ProtectedRoute>} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;
