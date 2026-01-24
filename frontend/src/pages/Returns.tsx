import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import type { Order } from '../types';
import { Modal, Button, Form } from 'react-bootstrap';
import Swal from 'sweetalert2';

interface ReturnItemDraft {
    sku: string;
    product_name: string;
    max_qty: number;
    quantity: number;
    condition: string;
    reason: string;
}

// Standard return reasons (BigSeller-style)
const RETURN_REASONS = [
    'ลูกค้าเปลี่ยนใจ',
    'สินค้าไม่ตรงตามรูป/คำอธิบาย',
    'สินค้าเสียหาย/ชำรุด',
    'ส่งผิดสินค้า/สี/ขนาด',
    'สินค้าไม่ครบ',
    'สินค้าหมดอายุ',
    'ได้รับสินค้าช้าเกินไป',
    'ปัญหาจากขนส่ง',
    'อื่นๆ'
];

const CHANNELS = [
    { code: 'all', label: 'ทั้งหมด', badge: '', color: '' },
    { code: 'shopee', label: 'Shopee', badge: 'S', color: 'warning' },
    { code: 'lazada', label: 'Lazada', badge: 'L', color: 'primary' },
    { code: 'tiktok', label: 'TikTok', badge: 'T', color: 'dark' },
    { code: 'facebook', label: 'Facebook', badge: 'F', color: 'info' },
    { code: 'manual', label: 'Manual', badge: 'M', color: 'secondary' },
];

// BigSeller-style status tabs
const STATUS_TABS = [
    { key: 'pending', label: 'รอรับคืน', statuses: 'TO_RETURN,RETURN_INITIATED', color: 'warning', icon: 'bi-hourglass-split' },
    { key: 'received', label: 'รับคืนแล้ว', statuses: 'RETURNED', color: 'success', icon: 'bi-box-arrow-in-down' },
    { key: 'failed', label: 'จัดส่งล้มเหลว', statuses: 'DELIVERY_FAILED', color: 'danger', icon: 'bi-x-circle' },
    { key: 'all', label: 'ทั้งหมด', statuses: 'RETURNED,TO_RETURN,RETURN_INITIATED,DELIVERY_FAILED', color: 'secondary', icon: 'bi-list-ul' },
];

const Returns: React.FC = () => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Status counts for tabs
    const [statusCounts, setStatusCounts] = useState({
        pending: 0,
        received: 0,
        failed: 0,
        all: 0
    });

    // Filters
    const [activeStatusTab, setActiveStatusTab] = useState('pending');
    const [channel, setChannel] = useState('all');
    const [search, setSearch] = useState('');
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setMonth(d.getMonth() - 1);
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => {
        const today = new Date();
        return today.toISOString().split('T')[0];
    });
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [perPage] = useState(20);

    // Bulk selection
    const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());

    // Return Modal State
    const [showReturnModal, setShowReturnModal] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
    const [returnItems, setReturnItems] = useState<ReturnItemDraft[]>([]);
    const [returnNote, setReturnNote] = useState('');
    const [submitting, setSubmitting] = useState(false);

    // Load status counts
    const loadStatusCounts = useCallback(async () => {
        try {
            const params = new URLSearchParams();
            if (channel !== 'all') params.set('channel', channel);
            if (startDate) params.set('start_date', startDate);
            if (endDate) params.set('end_date', endDate);

            // Load counts for each status group
            const [pendingRes, receivedRes, failedRes] = await Promise.all([
                api.get(`/orders?status=TO_RETURN,RETURN_INITIATED&per_page=1&${params}`),
                api.get(`/orders?status=RETURNED&per_page=1&${params}`),
                api.get(`/orders?status=DELIVERY_FAILED&per_page=1&${params}`)
            ]);

            setStatusCounts({
                pending: pendingRes.data.total || 0,
                received: receivedRes.data.total || 0,
                failed: failedRes.data.total || 0,
                all: (pendingRes.data.total || 0) + (receivedRes.data.total || 0) + (failedRes.data.total || 0)
            });
        } catch (e) {
            console.error('Failed to load status counts:', e);
        }
    }, [channel, startDate, endDate]);

    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            const currentTab = STATUS_TABS.find(t => t.key === activeStatusTab);
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: perPage.toString(),
                status: currentTab?.statuses || 'RETURNED,TO_RETURN,RETURN_INITIATED,DELIVERY_FAILED',
                date_field: 'returned_at',  // Filter by returned_at date, not order_datetime
            });
            if (channel !== 'all') params.set('channel', channel);
            if (search) params.set('search', search);
            if (startDate) params.set('start_date', startDate);
            if (endDate) params.set('end_date', endDate);

            const response = await api.get(`/orders?${params}`);
            if (response.data && response.data.orders) {
                setOrders(response.data.orders);
                setTotal(response.data.total || 0);
            } else {
                setOrders([]);
            }
            setError(null);
        } catch (err) {
            console.error("Failed to fetch returns:", err);
            setError("Failed to load return orders");
        } finally {
            setLoading(false);
        }
    }, [page, perPage, channel, search, startDate, endDate, activeStatusTab]);

    useEffect(() => {
        fetchOrders();
        loadStatusCounts();
    }, [fetchOrders, loadStatusCounts]);

    // Reset selection when filters change
    useEffect(() => {
        setSelectedOrders(new Set());
    }, [activeStatusTab, channel, search, page]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        fetchOrders();
    };

    const getStatusBadge = (status: string) => {
        const classes: Record<string, string> = {
            'RETURNED': 'bg-success',
            'TO_RETURN': 'bg-warning text-dark',
            'RETURN_INITIATED': 'bg-warning text-dark',
            'DELIVERY_FAILED': 'bg-danger',
        };
        const labels: Record<string, string> = {
            'RETURNED': 'รับคืนแล้ว',
            'TO_RETURN': 'รอคืน',
            'RETURN_INITIATED': 'เริ่มคืน',
            'DELIVERY_FAILED': 'ส่งล้มเหลว',
        };
        return <span className={`badge ${classes[status] || 'bg-secondary'}`}>{labels[status] || status}</span>;
    };

    const getChannelBadge = (channelCode: string) => {
        const ch = CHANNELS.find(c => c.code === channelCode);
        if (!ch || !ch.badge) return <span className="badge bg-light text-dark border">{channelCode}</span>;
        return <span className={`badge bg-${ch.color}`}>{channelCode}</span>;
    };

    const totalPages = Math.ceil(total / perPage);

    // Bulk selection handlers
    const toggleSelectOrder = (orderId: string) => {
        const newSet = new Set(selectedOrders);
        if (newSet.has(orderId)) {
            newSet.delete(orderId);
        } else {
            newSet.add(orderId);
        }
        setSelectedOrders(newSet);
    };

    const toggleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedOrders(new Set(orders.map(o => o.id)));
        } else {
            setSelectedOrders(new Set());
        }
    };

    // Bulk mark as received
    const handleBulkMarkReceived = async () => {
        if (selectedOrders.size === 0) return;

        const confirmed = await Swal.fire({
            title: 'ยืนยันการรับคืน',
            text: `ต้องการเปลี่ยนสถานะ ${selectedOrders.size} รายการเป็น "รับคืนแล้ว"?`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'ยืนยัน',
            cancelButtonText: 'ยกเลิก'
        });

        if (!confirmed.isConfirmed) return;

        try {
            await api.post('/orders/batch-status', {
                ids: Array.from(selectedOrders),
                status: 'RETURNED'
            });
            Swal.fire('สำเร็จ', 'อัพเดตสถานะเรียบร้อย', 'success');
            setSelectedOrders(new Set());
            fetchOrders();
            loadStatusCounts();
        } catch (err) {
            Swal.fire('ผิดพลาด', 'ไม่สามารถอัพเดตสถานะได้', 'error');
        }
    };

    // Export to Excel
    const handleExport = () => {
        const currentTab = STATUS_TABS.find(t => t.key === activeStatusTab);
        let url = `http://localhost:9203/api/orders/export?status=${currentTab?.statuses || 'RETURNED,TO_RETURN,RETURN_INITIATED,DELIVERY_FAILED'}`;
        if (channel !== 'all') url += `&channel=${channel}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        if (search) url += `&search=${search}`;
        window.open(url, '_blank');
    };

    const handleOpenReturnModal = (order: Order) => {
        setSelectedOrder(order);
        setReturnItems((order.items || []).map(item => ({
            sku: item.sku,
            product_name: item.product_name || item.sku,
            max_qty: item.quantity,
            quantity: 0,
            condition: 'GOOD',
            reason: RETURN_REASONS[0]
        })));
        setReturnNote('');
        setShowReturnModal(true);
    };

    const handleReturnItemChange = (index: number, field: keyof ReturnItemDraft, value: string | number) => {
        const newItems = [...returnItems];
        newItems[index] = { ...newItems[index], [field]: value };
        setReturnItems(newItems);
    };

    const handleSubmitReturn = async () => {
        if (!selectedOrder) return;
        setSubmitting(true);
        try {
            const itemsToReturn = returnItems
                .filter(i => i.quantity > 0)
                .map(i => ({
                    sku: i.sku,
                    quantity: i.quantity,
                    condition: i.condition,
                    reason: i.reason
                }));

            if (itemsToReturn.length === 0) {
                Swal.fire('Warning', 'กรุณาเลือกสินค้าอย่างน้อย 1 รายการ', 'warning');
                setSubmitting(false);
                return;
            }

            await api.post(`/orders/${selectedOrder.id}/return`, {
                items: itemsToReturn,
                note: returnNote
            });

            Swal.fire('สำเร็จ', 'บันทึกการคืนสินค้าเรียบร้อย', 'success');
            setShowReturnModal(false);
            fetchOrders();
            loadStatusCounts();
        } catch (err: unknown) {
            console.error("Return failed:", err);
            const message = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to process return.';
            Swal.fire('Error', message, 'error');
        } finally {
            setSubmitting(false);
        }
    };

    const breadcrumb = (
        <li className="breadcrumb-item active" aria-current="page">สินค้าตีคืน</li>
    );

    return (
        <Layout
            title="สินค้าตีคืน (Returns)"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <button className="btn btn-outline-success" onClick={handleExport} title="Export to Excel">
                        <i className="bi bi-file-earmark-excel me-1"></i>Export
                    </button>
                    <button className="btn btn-outline-primary" onClick={() => { fetchOrders(); loadStatusCounts(); }} disabled={loading}>
                        <i className={`bi ${loading ? 'bi-arrow-repeat spin' : 'bi-arrow-clockwise'} me-1`}></i>รีเฟรช
                    </button>
                </div>
            }
        >
            {error && <div className="alert alert-danger">{error}</div>}

            {/* Summary Cards */}
            <div className="row g-3 mb-4">
                {STATUS_TABS.filter(t => t.key !== 'all').map(tab => (
                    <div className="col-md-4" key={tab.key}>
                        <div
                            className={`card border-0 shadow-sm h-100 cursor-pointer ${activeStatusTab === tab.key ? `border-${tab.color} border-2` : ''}`}
                            onClick={() => { setActiveStatusTab(tab.key); setPage(1); }}
                            style={{ cursor: 'pointer' }}
                        >
                            <div className="card-body text-center py-3">
                                <i className={`bi ${tab.icon} fs-3 text-${tab.color}`}></i>
                                <div className={`fs-2 fw-bold text-${tab.color}`}>
                                    {statusCounts[tab.key as keyof typeof statusCounts]}
                                </div>
                                <div className="text-muted small">{tab.label}</div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* BigSeller-Style Status Tabs */}
            <ul className="nav nav-tabs mb-3">
                {STATUS_TABS.map(tab => (
                    <li className="nav-item" key={tab.key}>
                        <button
                            className={`nav-link ${activeStatusTab === tab.key ? 'active' : ''}`}
                            onClick={() => { setActiveStatusTab(tab.key); setPage(1); }}
                        >
                            <i className={`bi ${tab.icon} me-1`}></i>
                            {tab.label}
                            <span className={`badge bg-${tab.color} ms-1`}>
                                {statusCounts[tab.key as keyof typeof statusCounts]}
                            </span>
                        </button>
                    </li>
                ))}
            </ul>

            {/* Filters */}
            <div className="card mb-3 border-0 shadow-sm">
                <div className="card-body py-2">
                    {/* Channel Pills */}
                    <div className="d-flex flex-wrap gap-2 mb-3">
                        {CHANNELS.map(ch => (
                            <button
                                key={ch.code}
                                className={`btn btn-sm ${channel === ch.code ? 'btn-primary' : 'btn-outline-secondary'}`}
                                onClick={() => { setChannel(ch.code); setPage(1); }}
                            >
                                {ch.badge && <span className={`badge bg-${ch.color} me-1`}>{ch.badge}</span>}
                                {ch.label}
                            </button>
                        ))}
                    </div>

                    {/* Search & Date Filters */}
                    <form onSubmit={handleSearch} className="row g-2 align-items-center">
                        <div className="col-md-3">
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={startDate}
                                onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
                            />
                        </div>
                        <div className="col-md-3">
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={endDate}
                                onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
                            />
                        </div>
                        <div className="col-md-4">
                            <div className="input-group input-group-sm">
                                <span className="input-group-text"><i className="bi bi-search"></i></span>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="ค้นหารหัส, ชื่อ, เบอร์..."
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="col-md-2">
                            <button type="submit" className="btn btn-primary btn-sm w-100">
                                <i className="bi bi-filter me-1"></i>กรอง
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            {/* Bulk Action Bar */}
            {selectedOrders.size > 0 && (
                <div className="alert alert-info d-flex justify-content-between align-items-center mb-3">
                    <span><strong>{selectedOrders.size}</strong> รายการถูกเลือก</span>
                    <div className="d-flex gap-2">
                        <button className="btn btn-sm btn-success" onClick={handleBulkMarkReceived}>
                            <i className="bi bi-check-circle me-1"></i>ยืนยันรับคืนแล้ว
                        </button>
                        <button className="btn btn-sm btn-outline-secondary" onClick={() => setSelectedOrders(new Set())}>
                            ยกเลิกการเลือก
                        </button>
                    </div>
                </div>
            )}

            {/* Returns Table */}
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-3 py-3" style={{ width: '40px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            checked={orders.length > 0 && selectedOrders.size === orders.length}
                                            onChange={(e) => toggleSelectAll(e.target.checked)}
                                        />
                                    </th>
                                    <th className="py-3">รหัสออเดอร์</th>
                                    <th className="py-3">ช่องทาง</th>
                                    <th className="py-3">ลูกค้า</th>
                                    <th className="py-3">รายการสินค้า</th>
                                    <th className="py-3 text-end">ยอดเงินคืน</th>
                                    <th className="py-3">สถานะ</th>
                                    <th className="py-3">วันที่สั่ง</th>
                                    <th className="py-3">วันที่ตีกลับ</th>
                                    <th className="pe-3 py-3" style={{ width: '100px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={10} className="text-center py-5 text-muted">
                                            <div className="spinner-border text-primary"></div>
                                            <div className="mt-2">กำลังโหลด...</div>
                                        </td>
                                    </tr>
                                ) : orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={10} className="text-center py-5 text-muted">
                                            <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                                            ไม่พบรายการสินค้าตีคืน
                                        </td>
                                    </tr>
                                ) : (
                                    orders.map((order) => (
                                        <tr key={order.id} className={selectedOrders.has(order.id) ? 'table-active' : ''}>
                                            <td className="ps-3">
                                                <input
                                                    type="checkbox"
                                                    className="form-check-input"
                                                    checked={selectedOrders.has(order.id)}
                                                    onChange={() => toggleSelectOrder(order.id)}
                                                />
                                            </td>
                                            <td>
                                                <Link to={`/orders/${order.id}`} className="fw-semibold text-decoration-none">
                                                    {order.external_order_id || order.id.substring(0, 8)}
                                                </Link>
                                            </td>
                                            <td>{getChannelBadge(order.channel_code)}</td>
                                            <td>
                                                <div className="fw-medium">{order.customer_name || 'Guest'}</div>
                                                <small className="text-muted">{order.customer_phone}</small>
                                            </td>
                                            <td>
                                                {(order.items || []).slice(0, 2).map((item, i) => (
                                                    <div key={i} className="small text-truncate" style={{ maxWidth: '200px' }}>
                                                        {item.sku} x {item.quantity}
                                                    </div>
                                                ))}
                                                {(order.items || []).length > 2 && (
                                                    <small className="text-muted">+{order.items.length - 2} รายการ</small>
                                                )}
                                            </td>
                                            <td className="text-end fw-bold text-danger">
                                                ฿{order.total_amount.toLocaleString()}
                                            </td>
                                            <td>{getStatusBadge(order.status_normalized)}</td>
                                            <td className="text-muted">
                                                <small>
                                                    {order.order_datetime
                                                        ? new Date(order.order_datetime).toLocaleDateString('th-TH')
                                                        : '-'
                                                    }
                                                </small>
                                            </td>
                                            <td>
                                                {(order as any).returned_at ? (
                                                    <span className="badge bg-warning text-dark">
                                                        {new Date((order as any).returned_at).toLocaleDateString('th-TH')}
                                                    </span>
                                                ) : (
                                                    <span className="text-muted">-</span>
                                                )}
                                            </td>
                                            <td className="pe-3">
                                                <Link to={`/orders/${order.id}`} className="btn btn-sm btn-outline-primary me-1" title="ดูรายละเอียด">
                                                    <i className="bi bi-eye"></i>
                                                </Link>
                                                <button
                                                    className="btn btn-sm btn-outline-danger"
                                                    title="จัดการการคืนสินค้า"
                                                    onClick={() => handleOpenReturnModal(order)}
                                                >
                                                    <i className="bi bi-arrow-return-left"></i>
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Pagination */}
                <div className="card-footer d-flex justify-content-between align-items-center">
                    <div className="text-muted small">
                        แสดง {orders.length > 0 ? (page - 1) * perPage + 1 : 0}-{Math.min(page * perPage, total)} จาก {total} รายการ
                    </div>
                    {totalPages > 1 && (
                        <nav>
                            <ul className="pagination pagination-sm mb-0">
                                <li className={`page-item ${page === 1 ? 'disabled' : ''}`}>
                                    <button className="page-link" onClick={() => setPage(page - 1)}>ก่อนหน้า</button>
                                </li>
                                {[...Array(Math.min(5, totalPages))].map((_, i) => (
                                    <li key={i + 1} className={`page-item ${page === i + 1 ? 'active' : ''}`}>
                                        <button className="page-link" onClick={() => setPage(i + 1)}>{i + 1}</button>
                                    </li>
                                ))}
                                <li className={`page-item ${page === totalPages ? 'disabled' : ''}`}>
                                    <button className="page-link" onClick={() => setPage(page + 1)}>ถัดไป</button>
                                </li>
                            </ul>
                        </nav>
                    )}
                </div>
            </div>

            {/* Process Return Modal */}
            <Modal show={showReturnModal} onHide={() => setShowReturnModal(false)} size="lg">
                <Modal.Header closeButton>
                    <Modal.Title>จัดการการคืนสินค้า (Order #{selectedOrder?.external_order_id})</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <p className="text-muted small">เลือกสินค้าที่ต้องการคืนและระบุสภาพสินค้าเพื่อจัดการสต๊อก</p>
                    <div className="table-responsive">
                        <table className="table table-bordered table-sm">
                            <thead className="bg-light">
                                <tr>
                                    <th>สินค้า</th>
                                    <th style={{ width: '80px' }}>ซื้อ</th>
                                    <th style={{ width: '80px' }}>คืน</th>
                                    <th style={{ width: '130px' }}>สภาพ</th>
                                    <th style={{ width: '200px' }}>เหตุผล</th>
                                </tr>
                            </thead>
                            <tbody>
                                {returnItems.map((item, index) => (
                                    <tr key={index}>
                                        <td>
                                            <div>{item.product_name}</div>
                                            <small className="text-muted">{item.sku}</small>
                                        </td>
                                        <td className="text-center">{item.max_qty}</td>
                                        <td>
                                            <input
                                                type="number"
                                                className="form-control form-control-sm"
                                                min="0"
                                                max={item.max_qty}
                                                value={item.quantity}
                                                onChange={(e) => handleReturnItemChange(index, 'quantity', parseInt(e.target.value) || 0)}
                                            />
                                        </td>
                                        <td>
                                            <select
                                                className="form-select form-select-sm"
                                                value={item.condition}
                                                onChange={(e) => handleReturnItemChange(index, 'condition', e.target.value)}
                                                disabled={item.quantity === 0}
                                            >
                                                <option value="GOOD">ปกติ (Restock)</option>
                                                <option value="DAMAGED">เสียหาย</option>
                                            </select>
                                        </td>
                                        <td>
                                            <select
                                                className="form-select form-select-sm"
                                                value={item.reason}
                                                onChange={(e) => handleReturnItemChange(index, 'reason', e.target.value)}
                                                disabled={item.quantity === 0}
                                            >
                                                {RETURN_REASONS.map(reason => (
                                                    <option key={reason} value={reason}>{reason}</option>
                                                ))}
                                            </select>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <Form.Group className="mb-3">
                        <Form.Label>หมายเหตุเพิ่มเติม</Form.Label>
                        <Form.Control
                            as="textarea"
                            rows={2}
                            value={returnNote}
                            onChange={(e) => setReturnNote(e.target.value)}
                            placeholder="เช่น ลูกค้าแจ้งว่าส่งผิดสี..."
                        />
                    </Form.Group>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowReturnModal(false)}>
                        ยกเลิก
                    </Button>
                    <Button
                        variant="primary"
                        onClick={handleSubmitReturn}
                        disabled={submitting || returnItems.every(i => i.quantity === 0)}
                    >
                        {submitting ? <span className="spinner-border spinner-border-sm me-2" /> : <i className="bi bi-check-circle me-1"></i>}
                        ยืนยันการคืน
                    </Button>
                </Modal.Footer>
            </Modal>
        </Layout>
    );
};

export default Returns;
