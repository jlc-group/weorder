import React, { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import type { PlatformConfig } from '../types';
import Swal from 'sweetalert2';

const PLATFORM_COLORS: Record<string, string> = {
    shopee: '#EE4D2D',
    lazada: '#0f146d',
    tiktok: '#000000',
    facebook: '#1877F2',
    manual: '#6c757d'
};

const Settings: React.FC = () => {
    const [platforms, setPlatforms] = useState<PlatformConfig[]>([]);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState<string | null>(null); // Platform ID being synced

    // Edit modal state
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingPlatform, setEditingPlatform] = useState<PlatformConfig | null>(null);
    const [editForm, setEditForm] = useState({
        shop_name: '',
        is_active: true,
        sync_enabled: true
    });

    const fetchPlatforms = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get('/integrations/platforms');
            setPlatforms(res.data || []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    const handleSyncAll = async () => {
        setSyncing('all');
        try {
            await api.post('/integrations/sync-all');
            Swal.fire('สำเร็จ', 'เริ่มซิงค์ทุกแพลตฟอร์มแล้ว', 'success');
            setTimeout(() => fetchPlatforms(), 2000);
        } catch {
            Swal.fire('ผิดพลาด', 'ไม่สามารถเริ่มซิงค์ได้', 'error');
        } finally {
            setSyncing(null);
        }
    };

    const handleSyncPlatform = async (platformId: string) => {
        setSyncing(platformId);
        try {
            await api.post(`/integrations/platforms/${platformId}/sync`);
            Swal.fire('สำเร็จ', 'เริ่มซิงค์แล้ว', 'success');
            setTimeout(() => fetchPlatforms(), 2000);
        } catch {
            Swal.fire('ผิดพลาด', 'ไม่สามารถซิงค์ได้', 'error');
        } finally {
            setSyncing(null);
        }
    };

    const openEditModal = (platform: PlatformConfig) => {
        setEditingPlatform(platform);
        setEditForm({
            shop_name: platform.shop_name,
            is_active: platform.is_active,
            sync_enabled: platform.sync_enabled
        });
        setShowEditModal(true);
    };

    const handleSaveEdit = async () => {
        if (!editingPlatform) return;
        try {
            await api.put(`/integrations/platforms/${editingPlatform.id}`, editForm);
            setShowEditModal(false);
            fetchPlatforms();
            Swal.fire('สำเร็จ', 'บันทึกการตั้งค่าแล้ว', 'success');
        } catch {
            Swal.fire('ผิดพลาด', 'ไม่สามารถบันทึกได้', 'error');
        }
    };

    const handleToggleSyncEnabled = async (platform: PlatformConfig) => {
        try {
            await api.put(`/integrations/platforms/${platform.id}`, {
                sync_enabled: !platform.sync_enabled
            });
            fetchPlatforms();
        } catch {
            Swal.fire('ผิดพลาด', 'ไม่สามารถเปลี่ยนสถานะได้', 'error');
        }
    };

    const handleDisconnect = async (platform: PlatformConfig) => {
        const result = await Swal.fire({
            title: 'ยกเลิกการเชื่อมต่อ',
            text: `ต้องการยกเลิกการเชื่อมต่อ ${platform.platform} - ${platform.shop_name}?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'ยกเลิกการเชื่อมต่อ',
            cancelButtonText: 'ไม่',
            confirmButtonColor: '#dc3545'
        });

        if (result.isConfirmed) {
            try {
                await api.delete(`/integrations/platforms/${platform.id}`);
                fetchPlatforms();
                Swal.fire('สำเร็จ', 'ยกเลิกการเชื่อมต่อแล้ว', 'success');
            } catch {
                Swal.fire('ผิดพลาด', 'ไม่สามารถยกเลิกได้', 'error');
            }
        }
    };

    useEffect(() => {
        fetchPlatforms();
    }, [fetchPlatforms]);

    const breadcrumb = <li className="breadcrumb-item active">ตั้งค่า</li>;

    // Summary
    const activePlatforms = platforms.filter(p => p.is_active).length;
    const syncEnabledCount = platforms.filter(p => p.sync_enabled).length;

    return (
        <Layout
            title="ตั้งค่าการเชื่อมต่อ"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <button className="btn btn-outline-primary" onClick={fetchPlatforms} disabled={loading}>
                        <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                    </button>
                    <button className="btn btn-success" onClick={handleSyncAll} disabled={syncing !== null}>
                        <i className={`bi bi-cloud-arrow-down me-2 ${syncing === 'all' ? 'spin' : ''}`}></i>
                        Sync All
                    </button>
                </div>
            }
        >
            {/* Summary Cards */}
            <div className="row g-3 mb-4">
                <div className="col-md-4">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-2 fw-bold text-primary">{platforms.length}</div>
                            <div className="text-muted small">แพลตฟอร์มทั้งหมด</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-2 fw-bold text-success">{activePlatforms}</div>
                            <div className="text-muted small">เปิดใช้งาน</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-2 fw-bold text-info">{syncEnabledCount}</div>
                            <div className="text-muted small">เปิด Auto Sync</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Platforms Grid */}
            <div className="row g-4">
                {loading && platforms.length === 0 ? (
                    <div className="col-12 text-center py-5">
                        <div className="spinner-border text-primary"></div>
                        <div className="mt-2 text-muted">กำลังโหลด...</div>
                    </div>
                ) : platforms.length === 0 ? (
                    <div className="col-12 text-center py-5 text-muted">
                        <i className="bi bi-plug fs-1 d-block mb-2"></i>
                        ยังไม่มีการเชื่อมต่อ
                    </div>
                ) : (
                    platforms.map((p) => (
                        <div className="col-md-6 col-lg-4" key={p.id}>
                            <div className="card border-0 shadow-sm h-100">
                                <div
                                    className="card-header text-white py-3"
                                    style={{ backgroundColor: PLATFORM_COLORS[p.platform] || '#6c757d' }}
                                >
                                    <div className="d-flex justify-content-between align-items-center">
                                        <h5 className="mb-0 text-capitalize">
                                            <i className="bi bi-shop me-2"></i>
                                            {p.platform}
                                        </h5>
                                        {p.is_active ? (
                                            <span className="badge bg-light text-dark">Active</span>
                                        ) : (
                                            <span className="badge bg-danger">Inactive</span>
                                        )}
                                    </div>
                                </div>
                                <div className="card-body">
                                    <h6 className="fw-bold mb-3">{p.shop_name}</h6>

                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                        <span className="text-muted small">Auto Sync</span>
                                        <div className="form-check form-switch mb-0">
                                            <input
                                                type="checkbox"
                                                className="form-check-input"
                                                checked={p.sync_enabled}
                                                onChange={() => handleToggleSyncEnabled(p)}
                                                role="switch"
                                            />
                                        </div>
                                    </div>

                                    <div className="d-flex justify-content-between align-items-center mb-3">
                                        <span className="text-muted small">Last Sync</span>
                                        <span className="small">
                                            {p.last_sync_at
                                                ? new Date(p.last_sync_at).toLocaleString('th-TH')
                                                : 'ยังไม่เคย'}
                                        </span>
                                    </div>
                                </div>
                                <div className="card-footer bg-white border-0 py-3">
                                    <div className="d-flex gap-2">
                                        <button
                                            className="btn btn-sm btn-outline-primary flex-fill"
                                            onClick={() => handleSyncPlatform(p.id)}
                                            disabled={syncing !== null}
                                        >
                                            <i className={`bi bi-arrow-repeat ${syncing === p.id ? 'spin' : ''} me-1`}></i>
                                            Sync
                                        </button>
                                        <button
                                            className="btn btn-sm btn-outline-secondary"
                                            onClick={() => openEditModal(p)}
                                        >
                                            <i className="bi bi-gear"></i>
                                        </button>
                                        <button
                                            className="btn btn-sm btn-outline-danger"
                                            onClick={() => handleDisconnect(p)}
                                        >
                                            <i className="bi bi-x-lg"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Add Connection Card */}
            <div className="row mt-4">
                <div className="col-md-6 col-lg-4">
                    <div className="card border-dashed border-2 h-100" style={{ borderStyle: 'dashed', cursor: 'pointer' }}>
                        <div className="card-body text-center text-muted py-5">
                            <i className="bi bi-plus-circle fs-1 d-block mb-2"></i>
                            <span>เพิ่มการเชื่อมต่อ</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Edit Modal */}
            {showEditModal && editingPlatform && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    <i className="bi bi-gear me-2"></i>
                                    ตั้งค่า {editingPlatform.platform}
                                </h5>
                                <button type="button" className="btn-close" onClick={() => setShowEditModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="mb-3">
                                    <label className="form-label">ชื่อร้าน</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={editForm.shop_name}
                                        onChange={(e) => setEditForm({ ...editForm, shop_name: e.target.value })}
                                    />
                                </div>

                                <div className="form-check form-switch mb-3">
                                    <input
                                        type="checkbox"
                                        className="form-check-input"
                                        id="isActive"
                                        checked={editForm.is_active}
                                        onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                                    />
                                    <label className="form-check-label" htmlFor="isActive">
                                        เปิดใช้งาน
                                    </label>
                                </div>

                                <div className="form-check form-switch mb-3">
                                    <input
                                        type="checkbox"
                                        className="form-check-input"
                                        id="syncEnabled"
                                        checked={editForm.sync_enabled}
                                        onChange={(e) => setEditForm({ ...editForm, sync_enabled: e.target.checked })}
                                    />
                                    <label className="form-check-label" htmlFor="syncEnabled">
                                        Auto Sync (ซิงค์อัตโนมัติ)
                                    </label>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                                    ยกเลิก
                                </button>
                                <button type="button" className="btn btn-primary" onClick={handleSaveEdit}>
                                    <i className="bi bi-check-lg me-1"></i>บันทึก
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Settings;
