import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';

interface LayoutProps {
    children: React.ReactNode;
    title?: string;
    breadcrumb?: React.ReactNode;
    actions?: React.ReactNode;
}

interface SyncHealth {
    overall_status: 'healthy' | 'warning' | 'critical';
    issues: string[];
}

const Layout: React.FC<LayoutProps> = ({ children, title = "WeOrder", breadcrumb, actions }) => {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [syncHealth, setSyncHealth] = useState<SyncHealth | null>(null);
    const [healthLoading, setHealthLoading] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    // Close sidebar on route change
    const location = useLocation();
    useEffect(() => {
        setSidebarOpen(false);
    }, [location]);

    // Update clock
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Fetch sync health status - Manual refresh function
    const fetchHealth = async () => {
        setHealthLoading(true);
        try {
            const { data } = await api.get('/reconciliation/health');
            setSyncHealth({
                overall_status: data.overall_status,
                issues: data.issues || []
            });
        } catch (e) {
            // Silently fail - don't block UI
        } finally {
            setHealthLoading(false);
        }
    };

    useEffect(() => {
        fetchHealth();
        // Auto-refresh every 30 minutes (ช่วงใช้งานจริง 9.00-13.00, นอกเหนือจากนั้นใช้ manual)
        const interval = setInterval(fetchHealth, 30 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const formatDate = (date: Date) => {
        return date.toLocaleString('th-TH', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <>
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            <div className="main-content">
                {/* Top Navbar */}
                <nav className="top-navbar">
                    <div className="d-flex align-items-center">
                        <button
                            className="btn btn-link text-dark d-lg-none me-2 p-0"
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                        >
                            <i className="bi bi-list fs-4"></i>
                        </button>
                        <nav aria-label="breadcrumb">
                            <ol className="breadcrumb mb-0">
                                <li className="breadcrumb-item">
                                    <span className="text-decoration-none text-dark fw-medium">WeOrder</span>
                                </li>
                                {breadcrumb}
                            </ol>
                        </nav>
                    </div>

                    <div className="d-flex align-items-center gap-3">
                        {/* Manual Sync Health Check Button */}
                        <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={fetchHealth}
                            disabled={healthLoading}
                            title="คลิกเพื่อ check สถานะ sync (auto check ทุก 30 นาที)"
                        >
                            <i className={`bi ${healthLoading ? 'bi-arrow-repeat spin' : 'bi-arrow-clockwise'}`}></i>
                        </button>
                        {/* Sync Health Indicator */}
                        {syncHealth && syncHealth.overall_status !== 'healthy' && (
                            <Link
                                to="/report/sync-health"
                                className={`btn btn-sm ${syncHealth.overall_status === 'critical' ? 'btn-danger' : 'btn-warning'}`}
                                title={syncHealth.issues.join(', ')}
                            >
                                <i className="bi bi-exclamation-triangle me-1"></i>
                                Sync {syncHealth.overall_status === 'critical' ? 'Error' : 'Warning'}
                                <span className="badge bg-light text-dark ms-1">{syncHealth.issues.length}</span>
                            </Link>
                        )}
                        <span className="text-muted small">
                            <i className="bi bi-clock me-1"></i>
                            {formatDate(currentTime)}
                        </span>
                        {user && (
                            <div className="dropdown" ref={dropdownRef}>
                                <button
                                    className="btn btn-sm btn-outline-secondary dropdown-toggle"
                                    type="button"
                                    onClick={() => setDropdownOpen(!dropdownOpen)}
                                >
                                    <i className="bi bi-person-circle me-1"></i>
                                    {user.username}
                                </button>
                                {dropdownOpen && (
                                    <ul className="dropdown-menu dropdown-menu-end show" style={{ display: 'block', position: 'absolute', right: 0 }}>
                                        <li>
                                            <span className="dropdown-item-text small text-muted">
                                                {user.full_name || user.username}
                                            </span>
                                        </li>
                                        <li><hr className="dropdown-divider" /></li>
                                        <li>
                                            <button className="dropdown-item" onClick={handleLogout}>
                                                <i className="bi bi-box-arrow-right me-2"></i>
                                                ออกจากระบบ
                                            </button>
                                        </li>
                                    </ul>
                                )}
                            </div>
                        )}
                    </div>
                </nav>

                {/* Page Content */}
                <div className="page-content">
                    <div className="page-header">
                        <h1 className="page-title">{title}</h1>
                        <div>{actions}</div>
                    </div>
                    {children}
                </div>
            </div>
        </>
    );
};

export default Layout;

