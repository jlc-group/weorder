import React, { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import type { Promotion } from '../types';
import Swal from 'sweetalert2';

// Promotion types
const CONDITION_TYPES = [
    { value: 'PERCENTAGE', label: 'ส่วนลด %', icon: 'bi-percent' },
    { value: 'FIXED_AMOUNT', label: 'ส่วนลดบาท', icon: 'bi-cash' },
    { value: 'FREE_SHIPPING', label: 'ส่งฟรี', icon: 'bi-truck' },
    { value: 'BUY_X_GET_Y', label: 'ซื้อ X แถม Y', icon: 'bi-gift' },
    { value: 'BUNDLE', label: 'Bundle Deal', icon: 'bi-box2-heart' },
];

interface PromotionForm {
    name: string;
    description: string;
    condition_type: string;
    discount_value: number;
    min_order_amount: number;
    max_discount: number;
    start_at: string;
    end_at: string;
    is_active: boolean;
    applicable_skus: string[];
    channels: string[];
}

const CHANNELS = ['shopee', 'lazada', 'tiktok', 'facebook', 'manual'];

const Promotions: React.FC = () => {
    const [promotions, setPromotions] = useState<Promotion[]>([]);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState('');
    const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');

    // Modal state
    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<PromotionForm>({
        name: '',
        description: '',
        condition_type: 'PERCENTAGE',
        discount_value: 0,
        min_order_amount: 0,
        max_discount: 0,
        start_at: '',
        end_at: '',
        is_active: true,
        applicable_skus: [],
        channels: []
    });

    const fetchPromotions = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get('/promotions');
            setPromotions(res.data || []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPromotions();
    }, [fetchPromotions]);

    // Filter promotions
    const filteredPromotions = promotions.filter(p => {
        const matchSearch = p.name.toLowerCase().includes(search.toLowerCase());
        const matchStatus = filterStatus === 'all' ||
            (filterStatus === 'active' && p.is_active) ||
            (filterStatus === 'inactive' && !p.is_active);
        return matchSearch && matchStatus;
    });

    // Summary
    const summary = {
        total: promotions.length,
        active: promotions.filter(p => p.is_active).length,
        inactive: promotions.filter(p => !p.is_active).length,
    };

    // Open modal for create
    const openCreateModal = () => {
        setEditingId(null);
        setForm({
            name: '',
            description: '',
            condition_type: 'PERCENTAGE',
            discount_value: 10,
            min_order_amount: 0,
            max_discount: 0,
            start_at: new Date().toISOString().split('T')[0],
            end_at: '',
            is_active: true,
            applicable_skus: [],
            channels: []
        });
        setShowModal(true);
    };

    // Open modal for edit
    const openEditModal = (promo: Promotion) => {
        setEditingId(promo.id);
        setForm({
            name: promo.name,
            description: promo.description || '',
            condition_type: promo.condition_type,
            discount_value: promo.discount_value || 0,
            min_order_amount: promo.min_order_amount || 0,
            max_discount: promo.max_discount || 0,
            start_at: promo.start_at ? promo.start_at.split('T')[0] : '',
            end_at: promo.end_at ? promo.end_at.split('T')[0] : '',
            is_active: promo.is_active,
            applicable_skus: promo.applicable_skus || [],
            channels: promo.channels || []
        });
        setShowModal(true);
    };

    // Save promotion
    const handleSave = async () => {
        if (!form.name) {
            Swal.fire('ข้อผิดพลาด', 'กรุณากรอกชื่อโปรโมชั่น', 'error');
            return;
        }

        try {
            if (editingId) {
                await api.put(`/promotions/${editingId}`, form);
            } else {
                await api.post('/promotions', form);
            }
            setShowModal(false);
            fetchPromotions();
            Swal.fire('สำเร็จ', editingId ? 'อัพเดตโปรโมชั่นแล้ว' : 'สร้างโปรโมชั่นแล้ว', 'success');
        } catch (err) {
            console.error(err);
            Swal.fire('ผิดพลาด', 'ไม่สามารถบันทึกได้', 'error');
        }
    };

    // Toggle active
    const toggleActive = async (promo: Promotion) => {
        try {
            await api.put(`/promotions/${promo.id}`, { is_active: !promo.is_active });
            fetchPromotions();
        } catch (err) {
            console.error(err);
        }
    };

    // Delete promotion
    const handleDelete = async (id: string) => {
        const result = await Swal.fire({
            title: 'ยืนยันการลบ',
            text: 'คุณแน่ใจหรือไม่ที่จะลบโปรโมชั่นนี้?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'ลบ',
            cancelButtonText: 'ยกเลิก',
            confirmButtonColor: '#dc3545'
        });

        if (result.isConfirmed) {
            try {
                await api.delete(`/promotions/${id}`);
                fetchPromotions();
                Swal.fire('ลบแล้ว', 'โปรโมชั่นถูกลบเรียบร้อย', 'success');
            } catch (err) {
                console.error(err);
                Swal.fire('ผิดพลาด', 'ไม่สามารถลบได้', 'error');
            }
        }
    };

    const getConditionBadge = (type: string) => {
        const t = CONDITION_TYPES.find(c => c.value === type);
        return (
            <span className="badge bg-info text-dark">
                <i className={`bi ${t?.icon || 'bi-tag'} me-1`}></i>
                {t?.label || type}
            </span>
        );
    };

    const breadcrumb = <li className="breadcrumb-item active">โปรโมชั่น</li>;

    return (
        <Layout
            title="จัดการโปรโมชั่น"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <button className="btn btn-outline-primary" onClick={fetchPromotions} disabled={loading}>
                        <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                    </button>
                    <button className="btn btn-primary" onClick={openCreateModal}>
                        <i className="bi bi-plus-lg me-2"></i>สร้างโปรโมชั่น
                    </button>
                </div>
            }
        >
            {/* Summary Cards */}
            <div className="row g-3 mb-4">
                <div className="col-md-4">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-2 fw-bold text-primary">{summary.total}</div>
                            <div className="text-muted small">โปรโมชั่นทั้งหมด</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div
                        className={`card border-0 shadow-sm h-100 cursor-pointer ${filterStatus === 'active' ? 'border-success border-2' : ''}`}
                        onClick={() => setFilterStatus(filterStatus === 'active' ? 'all' : 'active')}
                        style={{ cursor: 'pointer' }}
                    >
                        <div className="card-body text-center py-3">
                            <div className="fs-2 fw-bold text-success">{summary.active}</div>
                            <div className="text-muted small">เปิดใช้งาน</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div
                        className={`card border-0 shadow-sm h-100 cursor-pointer ${filterStatus === 'inactive' ? 'border-secondary border-2' : ''}`}
                        onClick={() => setFilterStatus(filterStatus === 'inactive' ? 'all' : 'inactive')}
                        style={{ cursor: 'pointer' }}
                    >
                        <div className="card-body text-center py-3">
                            <div className="fs-2 fw-bold text-secondary">{summary.inactive}</div>
                            <div className="text-muted small">ปิดใช้งาน</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Search */}
            <div className="card border-0 shadow-sm mb-3">
                <div className="card-body py-3">
                    <div className="row g-2 align-items-center">
                        <div className="col-md-4">
                            <div className="input-group">
                                <span className="input-group-text"><i className="bi bi-search"></i></span>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="ค้นหาโปรโมชั่น..."
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="col-md-8 text-end">
                            <span className="text-muted">แสดง {filteredPromotions.length} รายการ</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Promotions Table */}
            <div className="card shadow-sm border-0">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-4 py-3">ชื่อโปรโมชั่น</th>
                                    <th className="py-3">ประเภท</th>
                                    <th className="py-3">ส่วนลด</th>
                                    <th className="py-3">ระยะเวลา</th>
                                    <th className="py-3 text-center">สถานะ</th>
                                    <th className="pe-4 py-3 text-end" style={{ width: '150px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && promotions.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="text-center py-5">
                                            <div className="spinner-border text-primary"></div>
                                            <div className="mt-2 text-muted">กำลังโหลด...</div>
                                        </td>
                                    </tr>
                                ) : filteredPromotions.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="text-center py-5 text-muted">
                                            <i className="bi bi-tag fs-1 d-block mb-2"></i>
                                            ไม่พบโปรโมชั่น
                                        </td>
                                    </tr>
                                ) : (
                                    filteredPromotions.map((p) => (
                                        <tr key={p.id}>
                                            <td className="ps-4">
                                                <div className="fw-bold">{p.name}</div>
                                                {p.description && <small className="text-muted">{p.description}</small>}
                                            </td>
                                            <td>{getConditionBadge(p.condition_type)}</td>
                                            <td className="fw-bold text-danger">
                                                {p.condition_type === 'PERCENTAGE' ? `${p.discount_value}%` :
                                                    p.condition_type === 'FIXED_AMOUNT' ? `฿${p.discount_value}` :
                                                        p.condition_type === 'FREE_SHIPPING' ? 'ส่งฟรี' : '-'}
                                            </td>
                                            <td className="small text-muted">
                                                {p.start_at ? new Date(p.start_at).toLocaleDateString('th-TH') : 'เริ่มทันที'}
                                                {' - '}
                                                {p.end_at ? new Date(p.end_at).toLocaleDateString('th-TH') : 'ไม่มีกำหนด'}
                                            </td>
                                            <td className="text-center">
                                                <div className="form-check form-switch d-inline-block">
                                                    <input
                                                        type="checkbox"
                                                        className="form-check-input"
                                                        checked={p.is_active}
                                                        onChange={() => toggleActive(p)}
                                                        role="switch"
                                                    />
                                                </div>
                                            </td>
                                            <td className="text-end pe-4">
                                                <button
                                                    className="btn btn-sm btn-outline-primary me-1"
                                                    onClick={() => openEditModal(p)}
                                                    title="แก้ไข"
                                                >
                                                    <i className="bi bi-pencil"></i>
                                                </button>
                                                <button
                                                    className="btn btn-sm btn-outline-danger"
                                                    onClick={() => handleDelete(p.id)}
                                                    title="ลบ"
                                                >
                                                    <i className="bi bi-trash"></i>
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-lg">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    <i className="bi bi-tag me-2"></i>
                                    {editingId ? 'แก้ไขโปรโมชั่น' : 'สร้างโปรโมชั่นใหม่'}
                                </h5>
                                <button type="button" className="btn-close" onClick={() => setShowModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="row">
                                    <div className="col-md-8 mb-3">
                                        <label className="form-label">ชื่อโปรโมชั่น *</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={form.name}
                                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                                            placeholder="เช่น ลดสูงสุด 20%"
                                        />
                                    </div>
                                    <div className="col-md-4 mb-3">
                                        <label className="form-label">ประเภท</label>
                                        <select
                                            className="form-select"
                                            value={form.condition_type}
                                            onChange={(e) => setForm({ ...form, condition_type: e.target.value })}
                                        >
                                            {CONDITION_TYPES.map(t => (
                                                <option key={t.value} value={t.value}>{t.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="mb-3">
                                    <label className="form-label">รายละเอียด</label>
                                    <textarea
                                        className="form-control"
                                        rows={2}
                                        value={form.description}
                                        onChange={(e) => setForm({ ...form, description: e.target.value })}
                                        placeholder="รายละเอียดโปรโมชั่น..."
                                    />
                                </div>

                                <div className="row">
                                    <div className="col-md-4 mb-3">
                                        <label className="form-label">
                                            {form.condition_type === 'PERCENTAGE' ? 'เปอร์เซ็นต์ลด' : 'จำนวนเงินลด'}
                                        </label>
                                        <div className="input-group">
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={form.discount_value}
                                                onChange={(e) => setForm({ ...form, discount_value: parseFloat(e.target.value) || 0 })}
                                            />
                                            <span className="input-group-text">
                                                {form.condition_type === 'PERCENTAGE' ? '%' : '฿'}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="col-md-4 mb-3">
                                        <label className="form-label">ยอดขั้นต่ำ</label>
                                        <div className="input-group">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={form.min_order_amount}
                                                onChange={(e) => setForm({ ...form, min_order_amount: parseFloat(e.target.value) || 0 })}
                                            />
                                        </div>
                                    </div>
                                    <div className="col-md-4 mb-3">
                                        <label className="form-label">ลดสูงสุด</label>
                                        <div className="input-group">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={form.max_discount}
                                                onChange={(e) => setForm({ ...form, max_discount: parseFloat(e.target.value) || 0 })}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">วันเริ่มต้น</label>
                                        <input
                                            type="date"
                                            className="form-control"
                                            value={form.start_at}
                                            onChange={(e) => setForm({ ...form, start_at: e.target.value })}
                                        />
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">วันสิ้นสุด</label>
                                        <input
                                            type="date"
                                            className="form-control"
                                            value={form.end_at}
                                            onChange={(e) => setForm({ ...form, end_at: e.target.value })}
                                        />
                                    </div>
                                </div>

                                <div className="mb-3">
                                    <label className="form-label">ช่องทางที่ใช้ได้</label>
                                    <div className="d-flex flex-wrap gap-2">
                                        {CHANNELS.map(ch => (
                                            <div key={ch} className="form-check">
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    id={`ch-${ch}`}
                                                    checked={form.channels.includes(ch)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setForm({ ...form, channels: [...form.channels, ch] });
                                                        } else {
                                                            setForm({ ...form, channels: form.channels.filter(c => c !== ch) });
                                                        }
                                                    }}
                                                />
                                                <label className="form-check-label text-capitalize" htmlFor={`ch-${ch}`}>
                                                    {ch}
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                    <small className="text-muted">ไม่เลือก = ใช้ได้ทุกช่องทาง</small>
                                </div>

                                <div className="form-check">
                                    <input
                                        type="checkbox"
                                        className="form-check-input"
                                        id="isActive"
                                        checked={form.is_active}
                                        onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                                    />
                                    <label className="form-check-label" htmlFor="isActive">
                                        เปิดใช้งานทันที
                                    </label>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                                    ยกเลิก
                                </button>
                                <button type="button" className="btn btn-primary" onClick={handleSave}>
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

export default Promotions;
