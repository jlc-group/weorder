import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import { scanFeedback } from './mobileFeedback';
import './Mobile.css';

interface ScanLog {
    id: string;
    message: string;
    status: 'success' | 'error' | 'info';
    time: Date;
    orderId?: string;
}

const MobilePack: React.FC = () => {
    const navigate = useNavigate();
    const [barcode, setBarcode] = useState('');
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState<ScanLog[]>([]);
    const [autoPrint, setAutoPrint] = useState(true);
    const [lastStatus, setLastStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [todayCount, setTodayCount] = useState(0);

    const inputRef = useRef<HTMLInputElement>(null);

    // Auto-focus input
    useEffect(() => {
        inputRef.current?.focus();
    }, [loading]);

    const addLog = (message: string, status: 'success' | 'error' | 'info', orderId?: string) => {
        setLogs(prev => [{
            id: Math.random().toString(36).substr(2, 9),
            message,
            status,
            time: new Date(),
            orderId
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
            // Search order
            const { data } = await api.get('/orders', {
                params: { search: code, per_page: 2 }
            });

            const orders = data.orders || [];

            if (orders.length === 0) {
                addLog(`ไม่พบ: ${code}`, 'error');
                scanFeedback.error('ไม่พบ');
                setLoading(false);
                return;
            }

            // Find exact match
            let order = orders[0];
            if (orders.length > 1) {
                const exact = orders.find((o: any) =>
                    o.external_order_id === code || o.tracking_number === code
                );
                if (exact) order = exact;
            }

            // Check status
            if (order.status_normalized !== 'PAID') {
                if (['PACKING', 'READY_TO_SHIP', 'SHIPPED'].includes(order.status_normalized)) {
                    addLog(`แพ็คไปแล้ว: ${order.external_order_id}`, 'error');
                    scanFeedback.error('แพ็คไปแล้ว');
                } else {
                    addLog(`สถานะไม่ถูก: ${order.external_order_id} (${order.status_normalized})`, 'error');
                    scanFeedback.error('สถานะไม่ถูก');
                }
                setLoading(false);
                return;
            }

            // Update to PACKING
            await api.post('/orders/batch-status', {
                ids: [order.id],
                status: 'PACKING'
            });

            addLog(`✓ PACKED: ${order.external_order_id}`, 'success', order.id);
            scanFeedback.success('แพ็คสำเร็จ');
            setTodayCount(prev => prev + 1);

            // Auto print
            if (autoPrint) {
                window.open(`/api/orders/batch-labels?format=pdf&ids=${order.id}`, '_blank');
            }

        } catch (err) {
            console.error(err);
            addLog(`Error: ${code}`, 'error');
            scanFeedback.error('เกิดข้อผิดพลาด');
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
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
                    <i className="bi bi-box-seam-fill me-2" style={{ color: '#10b981' }}></i>
                    Pack
                </h1>
                <div style={{ width: 48 }}></div>
            </div>

            {/* Scan Box */}
            <div className={`mobile-scan-box ${lastStatus}`}>
                <h5 style={{ marginBottom: 16, fontWeight: 600, fontSize: '1.1rem' }}>
                    <i className="bi bi-upc-scan me-2"></i>
                    สแกนเพื่อแพ็ค
                </h5>
                <form onSubmit={handleScan}>
                    <input
                        ref={inputRef}
                        type="text"
                        className="mobile-scan-input"
                        placeholder="Tracking / Order ID"
                        value={barcode}
                        onChange={(e) => setBarcode(e.target.value)}
                        disabled={loading}
                        autoFocus
                    />
                </form>

                <div className="mobile-scan-status" style={{ marginTop: 16 }}>
                    {loading && (
                        <div className="spinner-border text-light spinner-border-sm"></div>
                    )}
                    {!loading && lastStatus === 'success' && (
                        <span className="animate-pulse">
                            <i className="bi bi-check-circle-fill me-2"></i>สำเร็จ!
                        </span>
                    )}
                    {!loading && lastStatus === 'error' && (
                        <span className="animate-shake">
                            <i className="bi bi-exclamation-triangle-fill me-2"></i>ผิดพลาด
                        </span>
                    )}
                    {!loading && lastStatus === 'idle' && (
                        <span style={{ opacity: 0.7 }}>รอสแกน...</span>
                    )}
                </div>
            </div>

            {/* Stats Bar */}
            <div className="mobile-stats-bar" style={{ marginTop: 16, marginBottom: 16 }}>
                <div className="mobile-stat-item">
                    <div className="form-check form-switch" style={{ marginBottom: 0 }}>
                        <input
                            className="form-check-input"
                            type="checkbox"
                            id="autoPrint"
                            checked={autoPrint}
                            onChange={(e) => setAutoPrint(e.target.checked)}
                            style={{ width: 40, height: 20 }}
                        />
                        <label className="form-check-label" htmlFor="autoPrint" style={{ marginLeft: 4 }}>
                            <i className="bi bi-printer me-1"></i>Auto Print
                        </label>
                    </div>
                </div>
                <div className="mobile-stat-item">
                    <span>วันนี้:</span>
                    <span className="mobile-stat-value">{todayCount}</span>
                </div>
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

export default MobilePack;
