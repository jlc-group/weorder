import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api/client';
import './Mobile.css';

interface PendingCounts {
    toPack: number;
    toReturn: number;
    toPickItems: number;
    loading: boolean;
}

const MobileMenu: React.FC = () => {
    const navigate = useNavigate();
    const [counts, setCounts] = useState<PendingCounts>({
        toPack: 0,
        toReturn: 0,
        toPickItems: 0,
        loading: true
    });

    // Fetch pending counts on mount
    useEffect(() => {
        const fetchCounts = async () => {
            try {
                const [packRes, returnRes, pickRes] = await Promise.all([
                    // Orders with PAID status = ready to pack
                    api.get('/orders', { params: { status: 'PAID', per_page: 1 } }),
                    // Orders with return statuses
                    api.get('/orders', {
                        params: {
                            status: 'TO_RETURN,RETURN_INITIATED',
                            per_page: 1
                        }
                    }),
                    // Pick list summary
                    api.get('/orders/pick-list-summary', { params: { status: 'PAID' } })
                ]);

                setCounts({
                    toPack: packRes.data.total || 0,
                    toReturn: returnRes.data.total || 0,
                    toPickItems: pickRes.data.items?.length || 0,
                    loading: false
                });
            } catch (e) {
                console.error('Failed to fetch counts:', e);
                setCounts(prev => ({ ...prev, loading: false }));
            }
        };

        fetchCounts();
    }, []);

    const menuItems = [
        {
            title: 'แพ็คสินค้า',
            description: 'สแกน Tracking แพ็คพิมพ์ Label',
            path: '/mobile/pack',
            icon: 'bi-box-seam-fill',
            variant: 'pack',
            count: counts.toPack,
            countLabel: 'รอแพ็ค'
        },
        {
            title: 'ใบหยิบ',
            description: 'รายการสินค้าที่ต้องหยิบ',
            path: '/mobile/pick-list',
            icon: 'bi-list-check',
            variant: 'pick',
            count: counts.toPickItems,
            countLabel: 'SKUs'
        },
        {
            title: 'นับสต็อก',
            description: 'สแกนและนับจำนวนสินค้า',
            path: '/mobile/stock-count',
            icon: 'bi-clipboard-check-fill',
            variant: 'count',
            count: null,
            countLabel: ''
        },
        {
            title: 'รับคืน',
            description: 'สแกนรับสินค้าตีกลับ',
            path: '/mobile/return',
            icon: 'bi-arrow-return-left',
            variant: 'return',
            count: counts.toReturn,
            countLabel: 'รอคืน'
        },
        {
            title: 'ค้นหา',
            description: 'ค้นหา Order ทั้งหมด',
            path: '/mobile/search',
            icon: 'bi-search',
            variant: 'search',
            count: null,
            countLabel: ''
        },
        {
            title: 'พิมพ์ Label',
            description: 'พิมพ์แยกขนส่ง J&T/Flash',
            path: '/mobile/print-labels',
            icon: 'bi-printer-fill',
            variant: 'print',
            count: null,
            countLabel: ''
        }
    ];

    const totalPending = counts.toPack + counts.toReturn;

    return (
        <div className="mobile-container">
            {/* Header */}
            <div className="mobile-header">
                <button
                    className="mobile-header-back"
                    onClick={() => navigate('/dashboard')}
                >
                    <i className="bi bi-display"></i>
                </button>
                <h1 className="mobile-header-title">
                    <i className="bi bi-phone me-2"></i>
                    Mobile Station
                </h1>
                <div style={{ width: 48 }}></div>
            </div>

            {/* Quick Actions Hub - Pending Summary */}
            {!counts.loading && totalPending > 0 && (
                <div style={{
                    background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
                    borderRadius: 16,
                    padding: 16,
                    marginBottom: 16,
                    color: 'white'
                }}>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: 12
                    }}>
                        <span style={{ fontSize: '0.85rem', opacity: 0.8 }}>
                            <i className="bi bi-lightning-fill me-1" style={{ color: '#fbbf24' }}></i>
                            งานรอดำเนินการ
                        </span>
                        <span style={{
                            background: '#ef4444',
                            padding: '4px 12px',
                            borderRadius: 20,
                            fontSize: '0.85rem',
                            fontWeight: 700
                        }}>
                            {totalPending}
                        </span>
                    </div>
                    <div style={{ display: 'flex', gap: 12 }}>
                        {counts.toPack > 0 && (
                            <Link
                                to="/mobile/pack"
                                style={{
                                    flex: 1,
                                    background: 'rgba(16, 185, 129, 0.2)',
                                    borderRadius: 12,
                                    padding: 12,
                                    textAlign: 'center',
                                    textDecoration: 'none',
                                    color: 'white'
                                }}
                            >
                                <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                                    {counts.toPack}
                                </div>
                                <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>
                                    รอแพ็ค
                                </div>
                            </Link>
                        )}
                        {counts.toReturn > 0 && (
                            <Link
                                to="/mobile/return"
                                style={{
                                    flex: 1,
                                    background: 'rgba(245, 158, 11, 0.2)',
                                    borderRadius: 12,
                                    padding: 12,
                                    textAlign: 'center',
                                    textDecoration: 'none',
                                    color: 'white'
                                }}
                            >
                                <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                                    {counts.toReturn}
                                </div>
                                <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>
                                    รอคืน
                                </div>
                            </Link>
                        )}
                        {counts.toPickItems > 0 && (
                            <Link
                                to="/mobile/pick-list"
                                style={{
                                    flex: 1,
                                    background: 'rgba(59, 130, 246, 0.2)',
                                    borderRadius: 12,
                                    padding: 12,
                                    textAlign: 'center',
                                    textDecoration: 'none',
                                    color: 'white'
                                }}
                            >
                                <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                                    {counts.toPickItems}
                                </div>
                                <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>
                                    SKUs หยิบ
                                </div>
                            </Link>
                        )}
                    </div>
                </div>
            )}

            {/* Loading indicator */}
            {counts.loading && (
                <div style={{
                    background: 'rgba(255,255,255,0.8)',
                    borderRadius: 12,
                    padding: 16,
                    marginBottom: 16,
                    textAlign: 'center'
                }}>
                    <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                    <span style={{ color: '#64748b', fontSize: '0.85rem' }}>กำลังโหลด...</span>
                </div>
            )}

            {/* Menu Grid */}
            <div className="mobile-menu-grid">
                {menuItems.map((item) => (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`mobile-menu-card ${item.variant}`}
                        style={{ position: 'relative' }}
                    >
                        {/* Badge for pending count */}
                        {item.count !== null && item.count > 0 && (
                            <div style={{
                                position: 'absolute',
                                top: 8,
                                right: 8,
                                background: '#ef4444',
                                color: 'white',
                                padding: '2px 8px',
                                borderRadius: 12,
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                minWidth: 20,
                                textAlign: 'center'
                            }}>
                                {item.count}
                            </div>
                        )}
                        <div className={`mobile-menu-icon ${item.variant}`}>
                            <i className={`bi ${item.icon}`}></i>
                        </div>
                        <h3 className="mobile-menu-title">{item.title}</h3>
                        <p className="mobile-menu-desc">{item.description}</p>
                    </Link>
                ))}
            </div>

            {/* Info Footer */}
            <div style={{
                marginTop: 24,
                padding: '12px 16px',
                background: 'rgba(255,255,255,0.8)',
                borderRadius: 12,
                textAlign: 'center',
                fontSize: '0.8rem',
                color: '#64748b'
            }}>
                <i className="bi bi-info-circle me-1"></i>
                เลือกงานที่ต้องการทำ หรือสแกน Barcode โดยตรง
            </div>
        </div>
    );
};

export default MobileMenu;
