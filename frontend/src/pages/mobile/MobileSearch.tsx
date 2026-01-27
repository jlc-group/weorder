import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api/client';
import './Mobile.css';

interface OrderResult {
    id: string;
    external_order_id: string;
    tracking_number: string;
    customer_name: string;
    customer_phone: string;
    status_normalized: string;
    channel_code: string;
    total_amount: number;
    items: { sku: string; quantity: number; product_name: string }[];
    order_datetime: string;
}

const MobileSearch: React.FC = () => {
    const navigate = useNavigate();
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<OrderResult[]>([]);
    const [searched, setSearched] = useState(false);

    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        const query = searchText.trim();
        if (!query) return;

        setLoading(true);
        setSearched(true);

        try {
            const { data } = await api.get('/orders', {
                params: { search: query, per_page: 10 }
            });

            setResults(data.orders || []);
        } catch (err) {
            console.error(err);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const getChannelClass = (channel: string) => {
        const map: Record<string, string> = {
            'tiktok': 'channel-tiktok',
            'shopee': 'channel-shopee',
            'lazada': 'channel-lazada',
            'manual': 'channel-manual',
        };
        return map[channel] || 'channel-manual';
    };

    const getStatusClass = (status: string) => {
        const map: Record<string, string> = {
            'NEW': 'status-new',
            'PAID': 'status-paid',
            'PACKING': 'status-packing',
            'READY_TO_SHIP': 'status-ready',
            'SHIPPED': 'status-shipped',
            'DELIVERED': 'status-delivered',
            'CANCELLED': 'status-cancelled',
            'RETURNED': 'status-returned',
            'TO_RETURN': 'status-toreturn',
        };
        return map[status] || 'status-new';
    };

    const getStatusLabel = (status: string) => {
        const map: Record<string, string> = {
            'NEW': 'ใหม่',
            'PAID': 'จ่ายแล้ว',
            'PACKING': 'แพ็ค',
            'READY_TO_SHIP': 'รอส่ง',
            'SHIPPED': 'ส่งแล้ว',
            'DELIVERED': 'ส่งถึง',
            'CANCELLED': 'ยกเลิก',
            'RETURNED': 'คืน',
            'TO_RETURN': 'รอคืน',
        };
        return map[status] || status;
    };

    return (
        <div className="mobile-container">
            {/* Header */}
            <div className="mobile-header">
                <button
                    className="mobile-header-back"
                    onClick={() => navigate('/mobile')}
                >
                    <i className="bi bi-chevron-left"></i>
                </button>
                <h1 className="mobile-header-title">
                    <i className="bi bi-search me-2" style={{ color: '#8b5cf6' }}></i>
                    ค้นหา
                </h1>
                <div style={{ width: 48 }}></div>
            </div>

            {/* Search Bar */}
            <form onSubmit={handleSearch}>
                <div className="mobile-search-bar" style={{ marginBottom: 16 }}>
                    <div className="mobile-search-icon">
                        <i className="bi bi-search"></i>
                    </div>
                    <input
                        ref={inputRef}
                        type="text"
                        className="mobile-search-input"
                        placeholder="Tracking / Order ID / ชื่อ / เบอร์"
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        disabled={loading}
                        autoFocus
                    />
                    <button
                        type="submit"
                        className="mobile-search-btn"
                        disabled={loading || !searchText.trim()}
                    >
                        {loading ? (
                            <span className="spinner-border spinner-border-sm"></span>
                        ) : (
                            'ค้นหา'
                        )}
                    </button>
                </div>
            </form>

            {/* Initial State */}
            {!searched && (
                <div className="mobile-empty">
                    <i className="bi bi-search mobile-empty-icon"></i>
                    <p className="mobile-empty-text">สแกนหรือพิมพ์เพื่อค้นหา Order</p>
                </div>
            )}

            {/* Loading */}
            {searched && loading && (
                <div className="mobile-empty">
                    <div className="spinner-border text-primary"></div>
                    <p className="mobile-empty-text" style={{ marginTop: 12 }}>กำลังค้นหา...</p>
                </div>
            )}

            {/* No Results */}
            {searched && !loading && results.length === 0 && (
                <div className="mobile-empty">
                    <i className="bi bi-inbox mobile-empty-icon"></i>
                    <p className="mobile-empty-text">ไม่พบผลลัพธ์</p>
                </div>
            )}

            {/* Results */}
            {searched && !loading && results.length > 0 && (
                <div className="mobile-log-card">
                    <div className="mobile-log-header">
                        <i className="bi bi-list-ul"></i>
                        พบ {results.length} รายการ
                    </div>
                    <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                        {results.map(order => (
                            <Link
                                key={order.id}
                                to={`/orders/${order.id}`}
                                className="mobile-result-card"
                            >
                                <div className="mobile-result-header">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span className={`mobile-badge ${getChannelClass(order.channel_code)}`}>
                                            {order.channel_code?.toUpperCase()}
                                        </span>
                                        <span className="mobile-result-id">{order.external_order_id}</span>
                                    </div>
                                    <span className={`mobile-badge ${getStatusClass(order.status_normalized)}`}>
                                        {getStatusLabel(order.status_normalized)}
                                    </span>
                                </div>

                                <div className="mobile-result-info">
                                    <span>
                                        <i className="bi bi-person me-1"></i>
                                        {order.customer_name || 'ไม่ระบุ'}
                                    </span>
                                    {order.customer_phone && (
                                        <span>
                                            <i className="bi bi-telephone me-1"></i>
                                            {order.customer_phone}
                                        </span>
                                    )}
                                </div>

                                {order.tracking_number && (
                                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: 6 }}>
                                        <i className="bi bi-truck me-1"></i>
                                        {order.tracking_number}
                                    </div>
                                )}

                                <div className="mobile-result-footer">
                                    <div className="mobile-result-items">
                                        {order.items?.slice(0, 2).map((item, i) => (
                                            <span key={i}>
                                                {item.sku} x{item.quantity}
                                                {i < Math.min(order.items.length - 1, 1) && ', '}
                                            </span>
                                        ))}
                                        {(order.items?.length || 0) > 2 && (
                                            <span> +{order.items.length - 2}</span>
                                        )}
                                    </div>
                                    <span className="mobile-result-amount">
                                        ฿{order.total_amount?.toLocaleString()}
                                    </span>
                                </div>
                            </Link>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MobileSearch;
