import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
    children: React.ReactNode;
    title?: string;
    breadcrumb?: React.ReactNode;
    actions?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children, title = "WeOrder", breadcrumb, actions }) => {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());
    const [dropdownOpen, setDropdownOpen] = useState(false);
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

