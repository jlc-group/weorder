import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import { scanFeedback, vibrate } from './mobileFeedback';
import './Mobile.css';

interface ScanLog {
    id: string;
    message: string;
    status: 'success' | 'error' | 'info';
    time: Date;
}

interface ReturnOrder {
    id: string;
    external_order_id: string;
    customer_name: string;
    status_normalized: string;
    items: { sku: string; quantity: number; product_name: string }[];
}

const MobileReturn: React.FC = () => {
    const navigate = useNavigate();
    const [barcode, setBarcode] = useState('');
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState<ScanLog[]>([]);
    const [lastStatus, setLastStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [todayCount, setTodayCount] = useState(0);

    // Confirm modal
    const [showConfirm, setShowConfirm] = useState(false);
    const [pendingOrder, setPendingOrder] = useState<ReturnOrder | null>(null);

    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!showConfirm) {
            inputRef.current?.focus();
        }
    }, [loading, showConfirm]);

    const addLog = (message: string, status: 'success' | 'error' | 'info') => {
        setLogs(prev => [{
            id: Math.random().toString(36).substr(2, 9),
            message,
            status,
            time: new Date()
        }, ...prev].slice(0, 30));
        if (status !== 'info') setLastStatus(status);
    };

    const handleScan = async (e: React.FormEvent) => {
        e.preventDefault();
        const code = barcode.trim();
        if (!code) return;

        setLoading(true);
        setBarcode('');

        try {
            const { data } = await api.get('/orders', {
                params: {
                    search: code,
                    status: 'TO_RETURN,RETURN_INITIATED,DELIVERY_FAILED',
                    per_page: 5
                }
            });

            const orders = data.orders || [];

            if (orders.length === 0) {
                const { data: allData } = await api.get('/orders', {
                    params: { search: code, per_page: 2 }
                });

                if (allData.orders?.length > 0) {
                    const order = allData.orders[0];
                    if (order.status_normalized === 'RETURNED') {
                        addLog(`รับคืนไปแล้ว: ${order.external_order_id}`, 'error');
                        scanFeedback.error('รับคืนไปแล้ว');
                    } else {
                        addLog(`ไม่ใช่ Return: ${order.external_order_id} (${order.status_normalized})`, 'error');
                        scanFeedback.error('ไม่ใช่ออเดอร์ตีคืน');
                    }
                } else {
                    addLog(`ไม่พบ: ${code}`, 'error');
                    scanFeedback.error('ไม่พบ');
                }
                setLoading(false);
                return;
            }

            let order = orders[0];
            if (orders.length > 1) {
                const exact = orders.find((o: any) =>
                    o.external_order_id === code || o.tracking_number === code
                );
                if (exact) order = exact;
            }

            setPendingOrder(order);
            setShowConfirm(true);
            vibrate('light'); // Light vibration to confirm found

        } catch (err) {
            console.error(err);
            addLog(`Error: ${code}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    const confirmReturn = async () => {
        if (!pendingOrder) return;

        setLoading(true);
        try {
            await api.post('/orders/batch-status', {
                ids: [pendingOrder.id],
                status: 'RETURNED'
            });

            addLog(`✓ รับคืน: ${pendingOrder.external_order_id}`, 'success');
            scanFeedback.success('รับคืนสำเร็จ');
            setTodayCount(prev => prev + 1);
            setShowConfirm(false);
            setPendingOrder(null);

        } catch (err) {
            console.error(err);
            addLog(`Error updating: ${pendingOrder.external_order_id}`, 'error');
            scanFeedback.error('เกิดข้อผิดพลาด');
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    };

    const cancelReturn = () => {
        setShowConfirm(false);
        setPendingOrder(null);
        inputRef.current?.focus();
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
                    <i className="bi bi-arrow-return-left me-2" style={{ color: '#f59e0b' }}></i>
                    Return
                </h1>
                <div style={{ width: 48 }}></div>
            </div>

            {/* Scan Box */}
            <div style={{
                background: lastStatus === 'success'
                    ? 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)'
                    : lastStatus === 'error'
                        ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                        : 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                borderRadius: 20,
                padding: 24,
                textAlign: 'center',
                color: 'white',
                marginBottom: 16,
                transition: 'all 0.3s ease'
            }}>
                <h5 style={{ marginBottom: 16, fontWeight: 600, fontSize: '1.1rem' }}>
                    <i className="bi bi-box-arrow-in-down me-2"></i>
                    สแกนรับคืน
                </h5>
                <form onSubmit={handleScan}>
                    <input
                        ref={inputRef}
                        type="text"
                        className="mobile-scan-input"
                        placeholder="Tracking / Order ID"
                        value={barcode}
                        onChange={(e) => setBarcode(e.target.value)}
                        disabled={loading || showConfirm}
                        autoFocus
                    />
                </form>

                <div className="mobile-scan-status" style={{ marginTop: 16 }}>
                    {loading && <div className="spinner-border text-light spinner-border-sm"></div>}
                    {!loading && !showConfirm && lastStatus === 'success' && (
                        <span className="animate-pulse">
                            <i className="bi bi-check-circle-fill me-2"></i>รับคืนสำเร็จ!
                        </span>
                    )}
                    {!loading && !showConfirm && lastStatus === 'error' && (
                        <span className="animate-shake">
                            <i className="bi bi-exclamation-triangle-fill me-2"></i>ผิดพลาด
                        </span>
                    )}
                    {!loading && !showConfirm && lastStatus === 'idle' && (
                        <span style={{ opacity: 0.7 }}>รอสแกน...</span>
                    )}
                </div>
            </div>

            {/* Confirmation Card */}
            {showConfirm && pendingOrder && (
                <div className="mobile-confirm-card" style={{ marginBottom: 16 }}>
                    <div className="mobile-confirm-header">
                        <i className="bi bi-question-circle"></i>
                        ยืนยันการรับคืน
                    </div>
                    <div className="mobile-confirm-body">
                        <div style={{ marginBottom: 16 }}>
                            <div style={{ fontWeight: 700, fontSize: '1.25rem', color: '#1e293b' }}>
                                {pendingOrder.external_order_id}
                            </div>
                            <div style={{ color: '#64748b' }}>{pendingOrder.customer_name || 'ไม่ระบุชื่อ'}</div>
                        </div>

                        <div style={{ marginBottom: 16 }}>
                            <strong style={{ fontSize: '0.85rem', color: '#475569' }}>สินค้า:</strong>
                            <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
                                {pendingOrder.items?.slice(0, 3).map((item, i) => (
                                    <li key={i} style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 4 }}>
                                        • {item.sku} x{item.quantity}
                                    </li>
                                ))}
                                {(pendingOrder.items?.length || 0) > 3 && (
                                    <li style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                                        +{pendingOrder.items.length - 3} รายการ
                                    </li>
                                )}
                            </ul>
                        </div>

                        <div className="mobile-confirm-actions">
                            <button
                                className="mobile-btn success flex-1"
                                onClick={confirmReturn}
                                disabled={loading}
                            >
                                <i className="bi bi-check-lg"></i>
                                ยืนยัน
                            </button>
                            <button
                                className="mobile-btn outline flex-1"
                                onClick={cancelReturn}
                                disabled={loading}
                            >
                                ยกเลิก
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats */}
            <div className="mobile-stats-bar" style={{ marginBottom: 16 }}>
                <div className="mobile-stat-item">
                    <i className="bi bi-box-arrow-in-down"></i>
                    <span>รับคืนวันนี้</span>
                </div>
                <span className="mobile-stat-value">{todayCount}</span>
            </div>

            {/* Log History */}
            <div className="mobile-log-card">
                <div className="mobile-log-header">
                    <i className="bi bi-clock-history"></i>
                    ประวัติล่าสุด
                </div>
                <div className="mobile-log-list">
                    {logs.length === 0 ? (
                        <div className="mobile-empty" style={{ padding: 24 }}>
                            <i className="bi bi-inbox mobile-empty-icon"></i>
                            <p className="mobile-empty-text">ยังไม่มีรายการ</p>
                        </div>
                    ) : (
                        logs.map(log => (
                            <div key={log.id} className="mobile-log-item">
                                <span className={`mobile-log-message ${log.status}`}>
                                    {log.status === 'success' && <i className="bi bi-check me-1"></i>}
                                    {log.status === 'error' && <i className="bi bi-x me-1"></i>}
                                    {log.message}
                                </span>
                                <span className="mobile-log-time">
                                    {log.time.toLocaleTimeString('th-TH')}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

export default MobileReturn;
