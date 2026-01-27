import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface Batch {
    id: string;
    batch_number: number;
    batch_date: string;
    synced_at: string | null;
    cutoff_at: string;
    order_count: number;
    packed_count: number;
    printed_count: number;
    status: string;
    platform: string | null;
}

interface PendingInfo {
    pending_count: number;
    last_sync: string | null;
}

const PackingDashboard: React.FC = () => {
    const [batches, setBatches] = useState<Batch[]>([]);
    const [pendingInfo, setPendingInfo] = useState<PendingInfo | null>(null);
    const [_loading, _setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [creating, setCreating] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState<string>('');

    useEffect(() => {
        loadBatches();
        loadPendingCount();
    }, []);

    const loadBatches = async () => {
        try {
            const { data } = await api.get('/packing/batches');
            setBatches(data.batches || []);
        } catch (err) {
            console.error('Error loading batches:', err);
        }
    };

    const loadPendingCount = async () => {
        try {
            const params = selectedPlatform ? `?platform=${selectedPlatform}` : '';
            const { data } = await api.get(`/packing/pending-count${params}`);
            setPendingInfo(data);
        } catch (err) {
            console.error('Error loading pending count:', err);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        try {
            const params = selectedPlatform ? `?platform=${selectedPlatform}` : '';
            await api.post(`/packing/sync${params}`);
            await loadPendingCount();
            alert('Sync สำเร็จ! ข้อมูลอัปเดตแล้ว');
        } catch (err) {
            console.error('Error syncing:', err);
            alert('เกิดข้อผิดพลาด');
        } finally {
            setSyncing(false);
        }
    };

    const handleCreateBatch = async () => {
        if (!pendingInfo || pendingInfo.pending_count === 0) {
            alert('ไม่มี orders ที่รอแพ็ค');
            return;
        }

        setCreating(true);
        try {
            await api.post('/packing/batch', {
                platform: selectedPlatform || null,
                notes: null
            });
            await loadBatches();
            await loadPendingCount();
            alert('สร้างรอบแพ็คใหม่สำเร็จ!');
        } catch (err) {
            console.error('Error creating batch:', err);
            alert('เกิดข้อผิดพลาด');
        } finally {
            setCreating(false);
        }
    };

    const formatDateTime = (iso: string | null) => {
        if (!iso) return '-';
        return new Date(iso).toLocaleString('th-TH');
    };

    const getStatusBadge = (status: string) => {
        const colors: Record<string, string> = {
            'PENDING': 'bg-warning',
            'IN_PROGRESS': 'bg-primary',
            'COMPLETED': 'bg-success',
            'CANCELLED': 'bg-secondary'
        };
        return colors[status] || 'bg-secondary';
    };

    return (
        <Layout
            title="รอบแพ็คสินค้า"
            breadcrumb={
                <li className="breadcrumb-item active">Packing Dashboard</li>
            }
        >
            {/* Control Panel */}
            <div className="card mb-4">
                <div className="card-body">
                    <div className="row align-items-center">
                        <div className="col-md-3">
                            <label className="form-label">Platform</label>
                            <select
                                className="form-select"
                                value={selectedPlatform}
                                onChange={(e) => {
                                    setSelectedPlatform(e.target.value);
                                    setTimeout(loadPendingCount, 100);
                                }}
                            >
                                <option value="">ทั้งหมด</option>
                                <option value="tiktok">TikTok</option>
                                <option value="shopee">Shopee</option>
                                <option value="lazada">Lazada</option>
                            </select>
                        </div>

                        <div className="col-md-3">
                            <label className="form-label">รอแพ็ค</label>
                            <div className="h3 mb-0 text-primary">
                                {pendingInfo?.pending_count ?? '-'} <small className="text-muted fs-6">orders</small>
                            </div>
                        </div>

                        <div className="col-md-3">
                            <label className="form-label">อัพเดตล่าสุด</label>
                            <div className="text-muted">
                                {pendingInfo?.last_sync ? formatDateTime(pendingInfo.last_sync) : '-'}
                            </div>
                        </div>

                        <div className="col-md-3 d-flex gap-2 pt-4">
                            <button
                                className="btn btn-outline-primary flex-grow-1"
                                onClick={handleSync}
                                disabled={syncing}
                            >
                                {syncing ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2"></span>
                                        กำลัง Sync...
                                    </>
                                ) : (
                                    <>
                                        <i className="bi bi-arrow-repeat me-1"></i>
                                        ดึงข้อมูล
                                    </>
                                )}
                            </button>

                            <button
                                className="btn btn-success flex-grow-1"
                                onClick={handleCreateBatch}
                                disabled={creating || !pendingInfo?.pending_count}
                            >
                                {creating ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2"></span>
                                        กำลังสร้าง...
                                    </>
                                ) : (
                                    <>
                                        <i className="bi bi-plus-circle me-1"></i>
                                        ตัดรอบ
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Batch List */}
            <div className="card">
                <div className="card-header">
                    <h5 className="mb-0">รายการรอบแพ็ค</h5>
                </div>
                <div className="card-body p-0">
                    <table className="table table-hover mb-0">
                        <thead className="table-light">
                            <tr>
                                <th>รอบที่</th>
                                <th>วันที่</th>
                                <th>ตัดรอบเมื่อ</th>
                                <th>Platform</th>
                                <th className="text-center">จำนวน Orders</th>
                                <th className="text-center">แพ็คแล้ว</th>
                                <th className="text-center">พิมพ์แล้ว</th>
                                <th>สถานะ</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {batches.length === 0 ? (
                                <tr>
                                    <td colSpan={9} className="text-center py-5 text-muted">
                                        <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                                        ยังไม่มีรอบแพ็ค
                                    </td>
                                </tr>
                            ) : (
                                batches.map(batch => (
                                    <tr key={batch.id}>
                                        <td>
                                            <strong>#{batch.batch_number}</strong>
                                        </td>
                                        <td>{batch.batch_date}</td>
                                        <td>{formatDateTime(batch.cutoff_at)}</td>
                                        <td>
                                            {batch.platform ? (
                                                <span className="badge bg-secondary">{batch.platform}</span>
                                            ) : (
                                                <span className="text-muted">ทั้งหมด</span>
                                            )}
                                        </td>
                                        <td className="text-center">
                                            <strong>{batch.order_count}</strong>
                                        </td>
                                        <td className="text-center">
                                            {batch.packed_count} / {batch.order_count}
                                        </td>
                                        <td className="text-center">
                                            {batch.printed_count} / {batch.order_count}
                                        </td>
                                        <td>
                                            <span className={`badge ${getStatusBadge(batch.status)}`}>
                                                {batch.status}
                                            </span>
                                        </td>
                                        <td>
                                            <a href={`/packing/batch/${batch.id}`} className="btn btn-sm btn-outline-primary">
                                                <i className="bi bi-eye me-1"></i>
                                                ดูรายละเอียด
                                            </a>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </Layout>
    );
};

export default PackingDashboard;
