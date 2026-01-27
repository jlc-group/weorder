import React, { useState, useEffect, useRef } from 'react';
import api from '../api/client';

interface ScanToPackModalProps {
    isOpen: boolean;
    onClose: () => void;
    onOrderPacked?: () => void; // Callback to refresh parent list
}

interface ScanLog {
    id: string;
    message: string;
    status: 'success' | 'error';
    time: Date;
    orderId?: string;
}

const ScanToPackModal: React.FC<ScanToPackModalProps> = ({ isOpen, onClose, onOrderPacked }) => {
    const [barcode, setBarcode] = useState('');
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState<ScanLog[]>([]);
    const [autoPrint, setAutoPrint] = useState(true);
    const [lastScanStatus, setLastScanStatus] = useState<'idle' | 'success' | 'error'>('idle');

    const inputRef = useRef<HTMLInputElement>(null);

    // Auto-focus input when open or after scan
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [isOpen, loading]);

    // Keep focus
    const handleBlur = () => {
        if (isOpen && !loading) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const addLog = (message: string, status: 'success' | 'error', orderId?: string) => {
        setLogs(prev => [{
            id: Math.random().toString(36).substr(2, 9),
            message,
            status,
            time: new Date(),
            orderId
        }, ...prev].slice(0, 50)); // Keep last 50
        setLastScanStatus(status);
    };

    const playSound = (_type: 'success' | 'error') => {
        // Simple beep cues - in a real app would use Audio objects
        // For now, visual connection is enough
    };

    const handleScan = async (e: React.FormEvent) => {
        e.preventDefault();
        const code = barcode.trim();
        if (!code) return;

        setLoading(true);
        setBarcode(''); // Clear immediately for next scan

        try {
            // 1. Search for order
            const { data: searchData } = await api.get('/orders', {
                params: { search: code, per_page: 2 } // Limit to check ambiguity
            });

            const orders = searchData.orders || [];

            if (orders.length === 0) {
                addLog(`ไม่พบออเดอร์: ${code}`, 'error');
                playSound('error');
                setLoading(false);
                return;
            }

            if (orders.length > 1) {
                // If multiple, try strict match on external_id or tracking
                const exact = orders.find((o: any) =>
                    o.external_order_id === code || o.tracking_number === code
                );
                if (!exact) {
                    addLog(`ข้อมูลซ้ำซ้อน (${orders.length} รายการ): ${code}`, 'error');
                    playSound('error');
                    setLoading(false);
                    return;
                }
                processOrder(exact);
            } else {
                processOrder(orders[0]);
            }

        } catch (err) {
            console.error(err);
            addLog(`Error searching: ${code}`, 'error');
            playSound('error');
            setLoading(false);
        }
    };

    const processOrder = async (order: any) => {
        // 2. Check Status
        if (order.status_normalized !== 'PAID') { // Only pack NEW/PAID orders
            if (order.status_normalized === 'PACKING' || order.status_normalized === 'READY_TO_SHIP') {
                addLog(`ออเดอร์แพ็คไปแล้ว (${order.status_normalized}): ${order.external_order_id}`, 'error');
            } else {
                addLog(`สถานะไม่ถูกต้อง (${order.status_normalized}): ${order.external_order_id}`, 'error');
            }
            playSound('error');
            setLoading(false);
            return;
        }

        try {
            // 3. Update Status to PACKING
            await api.post('/orders/batch-status', {
                ids: [order.id],
                status: 'PACKING'
            });

            addLog(`PACKED: ${order.external_order_id}`, 'success', order.id);
            playSound('success');

            // 4. Auto Print (Optional)
            if (autoPrint) {
                // Trigger print - in a real app this might send to a local print service
                // For web, we usually open a window. 
                // Using a hidden iframe or new window that closes itself?
                window.open(`http://localhost:9203/api/orders/batch-labels?format=pdf&ids=${order.id}`, '_blank');
            }

            if (onOrderPacked) onOrderPacked();

        } catch (err) {
            console.error(err);
            addLog(`Failed to update status: ${order.external_order_id}`, 'error');
            playSound('error');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal show d-block"
            style={{ backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 2000 }}>
            <div className="container h-100 d-flex flex-col justify-content-center align-items-center p-4">

                {/* Header */}
                <div className="w-100 d-flex justify-content-between text-white mb-4" style={{ maxWidth: '800px' }}>
                    <h3><i className="bi bi-upc-scan me-2"></i>Scan to Pack</h3>
                    <button className="btn btn-close btn-close-white" onClick={onClose}></button>
                </div>

                {/* Main Scan Box */}
                <div className={`card w-100 shadow-lg border-0 mb-4 ${lastScanStatus === 'success' ? 'bg-success' : lastScanStatus === 'error' ? 'bg-danger' : 'bg-white'}`}
                    style={{ maxWidth: '800px', transition: 'background-color 0.3s' }}>
                    <div className="card-body p-5 text-center">
                        <div className="d-flex justify-content-center gap-3 align-items-center mb-4">
                            <input
                                ref={inputRef}
                                type="text"
                                className="form-control form-control-lg text-center fs-2 fw-bold"
                                placeholder="Scan Tracking No. / ID"
                                value={barcode}
                                onChange={e => setBarcode(e.target.value)}
                                onBlur={handleBlur}
                                disabled={loading}
                                style={{ height: '80px', letterSpacing: '2px' }}
                            />
                        </div>

                        {/* Status Message */}
                        {loading && <div className="spinner-border text-light" role="status"></div>}
                        {!loading && lastScanStatus === 'success' && (
                            <div className="text-white fs-4 fw-bold animate__animated animate__bounceIn">
                                <i className="bi bi-check-circle-fill me-2"></i> บันทึกสำเร็จ
                            </div>
                        )}
                        {!loading && lastScanStatus === 'error' && (
                            <div className="text-white fs-4 fw-bold animate__animated animate__shakeX">
                                <i className="bi bi-exclamation-triangle-fill me-2"></i> ผิดพลาด
                            </div>
                        )}
                        {!loading && lastScanStatus === 'idle' && (
                            <div className="text-muted">รอสแกน...</div>
                        )}

                        {/* Hidden Submit for Enter Key */}
                        <form onSubmit={handleScan}>
                            <input type="submit" style={{ display: 'none' }} />
                        </form>
                    </div>
                </div>

                {/* Controls */}
                <div className="card w-100 border-0 bg-dark text-white mb-4" style={{ maxWidth: '800px' }}>
                    <div className="card-body d-flex justify-content-between align-items-center">
                        <div className="form-check form-switch fs-5">
                            <input
                                className="form-check-input"
                                type="checkbox"
                                id="autoPrintSwitch"
                                checked={autoPrint}
                                onChange={e => setAutoPrint(e.target.checked)}
                            />
                            <label className="form-check-label" htmlFor="autoPrintSwitch">
                                <i className="bi bi-printer me-2"></i>Auto Print Label
                            </label>
                        </div>
                        <div className="text-muted small">
                            กด Enter เพื่อยืนยัน (กรณีไม่ได้ใช้ปืนยิง)
                        </div>
                    </div>
                </div>

                {/* Log History */}
                <div className="card w-100 border-0 flex-grow-1 overflow-hidden" style={{ maxWidth: '800px', minHeight: '200px' }}>
                    <div className="card-header bg-white fw-bold">
                        <i className="bi bi-clock-history me-2"></i>ประวัติการสแกนล่าสุด
                    </div>
                    <div className="card-body p-0 overflow-auto">
                        <table className="table table-striped mb-0">
                            <tbody>
                                {logs.map(log => (
                                    <tr key={log.id}>
                                        <td style={{ width: '80px' }} className="text-muted small">
                                            {log.time.toLocaleTimeString('th-TH')}
                                        </td>
                                        <td className={log.status === 'success' ? 'text-success fw-bold' : 'text-danger'}>
                                            {log.status === 'success' ? <i className="bi bi-check me-1"></i> : <i className="bi bi-x me-1"></i>}
                                            {log.message}
                                        </td>
                                    </tr>
                                ))}
                                {logs.length === 0 && (
                                    <tr>
                                        <td colSpan={2} className="text-center text-muted py-4">
                                            ยังไม่มีรายการ
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default ScanToPackModal;
