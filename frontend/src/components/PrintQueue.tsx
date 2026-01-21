import React, { useState, useEffect } from 'react';
import api from '../api/client';

interface QueueItem {
    order_id: string;
    external_order_id: string;
    channel_code: string;
    customer_name: string | null;
    added_at: string;
    priority: number;
}

interface PrintQueueProps {
    isOpen: boolean;
    onClose: () => void;
    onPrintAll: (orderIds: string[]) => void;
}

const PrintQueue: React.FC<PrintQueueProps> = ({ isOpen, onClose, onPrintAll }) => {
    const [queue, setQueue] = useState<QueueItem[]>([]);
    const [loading, setLoading] = useState(false);

    const loadQueue = async () => {
        try {
            const { data } = await api.get('/print-queue');
            setQueue(data.queue || []);
        } catch (e) {
            console.error('Failed to load print queue:', e);
        }
    };

    useEffect(() => {
        if (isOpen) {
            loadQueue();
        }
    }, [isOpen]);

    const removeFromQueue = async (orderId: string) => {
        try {
            await api.delete(`/print-queue/${orderId}`);
            loadQueue();
        } catch (e) {
            console.error('Failed to remove from queue:', e);
        }
    };

    const clearQueue = async () => {
        if (!window.confirm('ล้างคิวพิมพ์ทั้งหมด?')) return;
        try {
            await api.delete('/print-queue');
            loadQueue();
        } catch (e) {
            console.error('Failed to clear queue:', e);
        }
    };

    const handlePrintAll = async () => {
        if (queue.length === 0) {
            alert('คิวว่างเปล่า');
            return;
        }

        setLoading(true);
        try {
            const { data } = await api.post('/print-queue/print-all');
            if (data.success) {
                onPrintAll(data.order_ids);
                setQueue([]);
            }
        } catch (e) {
            console.error('Failed to print queue:', e);
        } finally {
            setLoading(false);
        }
    };

    const getChannelBadge = (channel: string) => {
        const colors: Record<string, string> = {
            'tiktok': 'bg-dark',
            'shopee': 'bg-warning text-dark',
            'lazada': 'bg-primary',
        };
        return colors[channel?.toLowerCase()] || 'bg-secondary';
    };

    if (!isOpen) return null;

    return (
        <div
            className="offcanvas offcanvas-end show"
            style={{ visibility: 'visible', width: '400px' }}
            tabIndex={-1}
        >
            <div className="offcanvas-header bg-primary text-white">
                <h5 className="offcanvas-title">
                    <i className="bi bi-printer me-2"></i>
                    คิวพิมพ์ ({queue.length})
                </h5>
                <button
                    type="button"
                    className="btn-close btn-close-white"
                    onClick={onClose}
                />
            </div>

            <div className="offcanvas-body p-0">
                {queue.length === 0 ? (
                    <div className="text-center text-muted py-5">
                        <i className="bi bi-inbox fs-1 d-block mb-3"></i>
                        <p>คิวว่างเปล่า</p>
                        <small>เลือก orders แล้วกด "เพิ่มเข้าคิว" เพื่อเพิ่ม</small>
                    </div>
                ) : (
                    <ul className="list-group list-group-flush">
                        {queue.map((item, index) => (
                            <li
                                key={item.order_id}
                                className="list-group-item d-flex justify-content-between align-items-center py-3"
                            >
                                <div className="d-flex align-items-center gap-2">
                                    <span className="badge bg-secondary">{index + 1}</span>
                                    <div>
                                        <span className={`badge ${getChannelBadge(item.channel_code)} me-1`}>
                                            {item.channel_code?.toUpperCase()}
                                        </span>
                                        <small className="text-muted d-block">
                                            {item.external_order_id}
                                        </small>
                                        {item.customer_name && (
                                            <small className="text-muted">
                                                {item.customer_name}
                                            </small>
                                        )}
                                    </div>
                                </div>
                                <button
                                    className="btn btn-sm btn-outline-danger"
                                    onClick={() => removeFromQueue(item.order_id)}
                                    title="ลบออกจากคิว"
                                >
                                    <i className="bi bi-x"></i>
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {queue.length > 0 && (
                <div className="offcanvas-footer p-3 border-top bg-light">
                    <div className="d-flex gap-2">
                        <button
                            className="btn btn-outline-danger flex-grow-1"
                            onClick={clearQueue}
                        >
                            <i className="bi bi-trash me-1"></i>
                            ล้างคิว
                        </button>
                        <button
                            className="btn btn-success flex-grow-1"
                            onClick={handlePrintAll}
                            disabled={loading}
                        >
                            <i className="bi bi-printer me-1"></i>
                            {loading ? 'กำลังพิมพ์...' : `พิมพ์ทั้งหมด (${queue.length})`}
                        </button>
                    </div>
                </div>
            )}

            {/* Backdrop */}
            <div
                className="offcanvas-backdrop fade show"
                onClick={onClose}
                style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: -1 }}
            />
        </div>
    );
};

export default PrintQueue;
