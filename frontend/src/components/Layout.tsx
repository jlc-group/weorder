import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

interface LayoutProps {
    children: React.ReactNode;
    title?: string;
    breadcrumb?: React.ReactNode;
    actions?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children, title = "WeOrder", breadcrumb, actions }) => {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());

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

    const formatDate = (date: Date) => {
        return date.toLocaleString('th-TH', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
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
