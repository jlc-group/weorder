import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface Manifest {
    id: string;
    manifest_number: string;
    platform: string;
    courier: string;
    status: 'OPEN' | 'CLOSED' | 'PICKED_UP';
    order_count: number;
    parcel_count: number;
    created_at: string;
    closed_at?: string;
    picked_up_at?: string;
}

interface ManifestItem {
    id: string;
    order_id: string;
    external_order_id: string;
    tracking_number: string;
    customer_name: string;
    added_at: string;
}

interface ManifestDetail extends Manifest {
    items: ManifestItem[];
}

const Manifests: React.FC = () => {
    const [manifests, setManifests] = useState<Manifest[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedManifest, setSelectedManifest] = useState<ManifestDetail | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);

    // Create Form
    const [createForm, setCreateForm] = useState({
        platform: 'shopee',
        courier: 'J&T Express',
        notes: ''
    });

    const loadManifests = async () => {
        setLoading(true);
        try {
            const { data } = await api.get('/manifests');
            setManifests(data.manifests || []);
        } catch (e) {
            console.error('Failed to load manifests:', e);
        } finally {
            setLoading(false);
        }
    };

    const loadManifestDetail = async (id: string) => {
        try {
            const { data } = await api.get(`/manifests/${id}`);
            setSelectedManifest(data);
            setShowDetailModal(true);
        } catch (e) {
            console.error('Failed to load manifest detail:', e);
            alert('ไม่สามารถโหลดข้อมูล Manifest ได้');
        }
    };

    const handleCreate = async () => {
        try {
            await api.post('/manifests', createForm);
            setShowCreateModal(false);
            loadManifests();
        } catch (e) {
            console.error('Failed to create manifest:', e);
            alert('เกิดข้อผิดพลาดในการสร้าง Manifest');
        }
    };

    const handleCloseManifest = async (id: string) => {
        if (!confirm('ยืนยันปิด Manifest? หลังจากปิดแล้วจะไม่สามารถเพิ่มออเดอร์ได้อีก')) return;
        try {
            await api.post(`/manifests/${id}/close`);
            if (selectedManifest?.id === id) {
                loadManifestDetail(id); // Reload detail
            }
            loadManifests(); // Reload list
        } catch (e) {
            console.error('Failed to close manifest:', e);
            alert('เกิดข้อผิดพลาด');
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('ยืนยันลบ Manifest? (ลบได้เฉพาะสถานะ OPEN และไม่มีออเดอร์)')) return;
        try {
            await api.delete(`/manifests/${id}`);
            loadManifests();
        } catch (e: any) {
            console.error('Failed to delete:', e);
            alert(e.response?.data?.detail || 'เกิดข้อผิดพลาด');
        }
    };

    const printManifest = (id: string) => {
        // TODO: Implement PDF print endpoint for Manifest
        alert(`กำลังพัฒนาระบบพิมพ์ใบ Manifest ID: ${id} (ใช้หน้าจอ Browser Print ไปก่อนได้)`);
        // window.open(`/api/manifests/${id}/print`, '_blank');
    };

    useEffect(() => {
        loadManifests();
    }, []);

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'OPEN': return <span className="badge bg-success">เปิดรับออเดอร์</span>;
            case 'CLOSED': return <span className="badge bg-secondary">ปิดแล้ว (รอรับ)</span>;
            case 'PICKED_UP': return <span className="badge bg-primary">ขนส่งรับแล้ว</span>;
            default: return <span className="badge bg-light text-dark">{status}</span>;
        }
    };

    return (
        <Layout
            title="Carrier Manifest (ใบส่งสินค้ารวม)"
            actions={
                <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                    <i className="bi bi-plus-lg me-2"></i>สร้างใบ Manifest ใหม่
                </button>
            }
        >
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover mb-0 align-middle">
                            <thead className="bg-light">
                                <tr>
                                    <th>เลขที่เอกสาร</th>
                                    <th>ขนส่ง / Platform</th>
                                    <th>สถานะ</th>
                                    <th>จำนวนพัสดุ</th>
                                    <th>สร้างเมื่อ</th>
                                    <th>ปิดรอบเมื่อ</th>
                                    <th>จัดการ</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan={7} className="text-center py-5">Loading...</td></tr>
                                ) : manifests.length === 0 ? (
                                    <tr><td colSpan={7} className="text-center py-5 text-muted">ยังไม่มีเอกสาร Manifest</td></tr>
                                ) : (
                                    manifests.map(m => (
                                        <tr key={m.id}>
                                            <td className="fw-mono fw-bold text-primary" style={{ cursor: 'pointer' }} onClick={() => loadManifestDetail(m.id)}>
                                                {m.manifest_number}
                                            </td>
                                            <td>
                                                <div className="fw-bold">{m.courier}</div>
                                                <small className="text-muted text-uppercase">{m.platform || 'Mixed'}</small>
                                            </td>
                                            <td>{getStatusBadge(m.status)}</td>
                                            <td>
                                                <span className="badge bg-light text-dark border">
                                                    {m.order_count} ชิ้น
                                                </span>
                                            </td>
                                            <td>{new Date(m.created_at).toLocaleDateString('th-TH', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</td>
                                            <td>{m.closed_at ? new Date(m.closed_at).toLocaleDateString('th-TH', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-'}</td>
                                            <td>
                                                <button className="btn btn-sm btn-outline-primary me-1" onClick={() => loadManifestDetail(m.id)}>
                                                    <i className="bi bi-eye"></i>
                                                </button>
                                                {m.status === 'OPEN' && m.order_count === 0 && (
                                                    <button className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(m.id)}>
                                                        <i className="bi bi-trash"></i>
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">สร้างใบ Manifest ใหม่</h5>
                                <button className="btn-close" onClick={() => setShowCreateModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="mb-3">
                                    <label className="form-label">Platform</label>
                                    <select
                                        className="form-select"
                                        value={createForm.platform}
                                        onChange={e => setCreateForm({ ...createForm, platform: e.target.value })}
                                    >
                                        <option value="shopee">Shopee</option>
                                        <option value="tiktok">TikTok</option>
                                        <option value="lazada">Lazada</option>
                                        <option value="mixed">รวมทุกช่องทาง (Mixed)</option>
                                    </select>
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">ขนส่ง (Courier)</label>
                                    <select
                                        className="form-select"
                                        value={createForm.courier}
                                        onChange={e => setCreateForm({ ...createForm, courier: e.target.value })}
                                    >
                                        <option value="J&T Express">J&T Express</option>
                                        <option value="Flash Express">Flash Express</option>
                                        <option value="Kerry Express">Kerry Express</option>
                                        <option value="Shopee Xpress">Shopee Xpress</option>
                                        <option value="Lazada Express">Lazada Express</option>
                                    </select>
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">หมายเหตุ</label>
                                    <textarea
                                        className="form-control"
                                        rows={2}
                                        value={createForm.notes}
                                        onChange={e => setCreateForm({ ...createForm, notes: e.target.value })}
                                    ></textarea>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>ยกเลิก</button>
                                <button className="btn btn-primary" onClick={handleCreate}>สร้างเอกสาร</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedManifest && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-xl modal-dialog-scrollable">
                        <div className="modal-content">
                            <div className="modal-header bg-light">
                                <div>
                                    <h5 className="modal-title fw-bold">
                                        Manifest: {selectedManifest.manifest_number}
                                    </h5>
                                    <div className="gap-2 d-flex mt-1">
                                        {getStatusBadge(selectedManifest.status)}
                                        <span className="badge bg-dark">{selectedManifest.courier}</span>
                                    </div>
                                </div>
                                <button className="btn-close" onClick={() => setShowDetailModal(false)}></button>
                            </div>
                            <div className="modal-body p-0">
                                <table className="table table-striped table-sm mb-0">
                                    <thead className="bg-light sticky-top">
                                        <tr>
                                            <th>ลำดับ</th>
                                            <th>Order ID</th>
                                            <th>Tracking No.</th>
                                            <th>ลูกค้า</th>
                                            <th>เวลาที่เพิ่ม</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {selectedManifest.items.length === 0 ? (
                                            <tr><td colSpan={5} className="text-center py-4">ไม่มีรายการพัสดุ</td></tr>
                                        ) : (
                                            selectedManifest.items.map((item, idx) => (
                                                <tr key={item.id}>
                                                    <td>{idx + 1}</td>
                                                    <td className="fw-mono">{item.external_order_id}</td>
                                                    <td className="fw-mono">{item.tracking_number || '-'}</td>
                                                    <td>{item.customer_name}</td>
                                                    <td>{new Date(item.added_at).toLocaleTimeString('th-TH')}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            <div className="modal-footer justify-content-between">
                                <div>
                                    <span className="fw-bold me-2">รวม: {selectedManifest.order_count} ชิ้น</span>
                                </div>
                                <div className="d-flex gap-2">
                                    {selectedManifest.status === 'OPEN' && (
                                        <button className="btn btn-warning" onClick={() => handleCloseManifest(selectedManifest.id)}>
                                            <i className="bi bi-lock-fill me-1"></i>ปิดรอบการส่ง (Close Manifest)
                                        </button>
                                    )}
                                    <button className="btn btn-dark" onClick={() => printManifest(selectedManifest.id)}>
                                        <i className="bi bi-printer me-1"></i>พิมพ์ใบสรุป
                                    </button>
                                    <button className="btn btn-secondary" onClick={() => setShowDetailModal(false)}>ปิด</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Manifests;
