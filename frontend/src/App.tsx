import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Orders from './pages/Orders';
import OrderCreate from './pages/OrderCreate';
import OrderDetail from './pages/OrderDetail';
import Products from './pages/Products';
import PlatformBundles from './pages/PlatformBundles';
import Stock from './pages/Stock';
import Packing from './pages/Packing';
import Promotions from './pages/Promotions';
import Finance from './pages/Finance';
import FinancePerformance from './pages/FinancePerformance';
import Settings from './pages/Settings';
import InvoiceRequest from './pages/InvoiceRequest';
import InvoiceManager from './pages/InvoiceManager';
import Returns from './pages/Returns';
import DailyOutbound from './pages/DailyOutbound';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />

        {/* Orders Routes */}
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/create" element={<OrderCreate />} />
        <Route path="/orders/:orderId" element={<OrderDetail />} />
        <Route path="/products" element={<Products />} />
        <Route path="/bundles" element={<PlatformBundles />} />
        <Route path="/stock" element={<Stock />} />
        <Route path="/packing" element={<Packing />} />
        <Route path="/returns" element={<Returns />} />
        <Route path="/promotions" element={<Promotions />} />
        <Route path="/finance" element={<Finance />} />
        <Route path="/finance/performance" element={<FinancePerformance />} />
        <Route path="/settings" element={<Settings />} />

        {/* Tax Invoice */}
        <Route path="/invoice-request" element={<InvoiceRequest />} />
        <Route path="/invoice-manager" element={<InvoiceManager />} />

        {/* Reports */}
        <Route path="/report/outbound" element={<DailyOutbound />} />

        <Route path="*" element={<Dashboard />} /> {/* Fallback */}
      </Routes>
    </Router>
  );
}

export default App;
