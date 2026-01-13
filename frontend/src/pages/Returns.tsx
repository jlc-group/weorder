import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import type { Order } from '../types';
import { Modal, Button, Form } from 'react-bootstrap';
import Swal from 'sweetalert2';
import { useCallback } from 'react';

interface ReturnItemDraft {
    sku: string;
    product_name: string;
    max_qty: number;
    quantity: number;
    condition: string;
    reason: string;
}

const CHANNELS = [
    { code: 'all', label: 'ทั้งหมด', badge: '' },
    { code: 'shopee', label: 'Shopee', badge: 'S', color: 'warning' },
    { code: 'lazada', label: 'Lazada', badge: 'L', color: 'primary' },
    { code: 'tiktok', label: 'TikTok', badge: 'T', color: 'dark' },
    { code: 'facebook', label: 'Facebook', badge: 'F', color: 'info' },
    { code: 'manual', label: 'Manual', badge: 'M', color: 'secondary' },
];

const Returns: React.FC = () => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [channel, setChannel] = useState('all');
    const [search, setSearch] = useState('');
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setMonth(d.getMonth() - 1); // Default last month for returns
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => {
        const today = new Date();
        return today.toISOString().split('T')[0];
    });
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [perPage] = useState(20);

    // Return Modal State
    const [showReturnModal, setShowReturnModal] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
    const [returnItems, setReturnItems] = useState<ReturnItemDraft[]>([]);
    const [returnNote, setReturnNote] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: perPage.toString(),
                status: 'RETURNED,TO_RETURN,RETURN_INITIATED,DELIVERY_FAILED',
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
    }, [page, perPage, channel, search, startDate, endDate]);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        fetchOrders();
    };

    const getStatusBadge = (status: string) => {
        const classes: Record<string, string> = {
            'RETURNED': 'bg-danger',
            'TO_RETURN': 'bg-warning text-dark',
            'RETURN_INITIATED': 'bg-warning text-dark',
            'COMPLETED': 'bg-success', // Refunded?
        };
        return <span className={`badge ${classes[status] || 'bg-secondary'}`}>{status}</span>;
    };

    const getChannelBadge = (channelCode: string) => {
        const ch = CHANNELS.find(c => c.code === channelCode);
        if (!ch || !ch.badge) return <span className="badge bg-light text-dark border">{channelCode}</span>;
        return <span className={`badge bg-${ch.color}`}>{channelCode}</span>;
    };

    const totalPages = Math.ceil(total / perPage);

    const handleOpenReturnModal = (order: Order) => {
        setSelectedOrder(order);
        setReturnItems((order.items || []).map(item => ({
            sku: item.sku,
            product_name: item.product_name || item.sku,
            max_qty: item.quantity,
            quantity: 0,
            condition: 'GOOD',
            reason: ''
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
            // Filter only items with Quantity > 0
            const itemsToReturn = returnItems
                .filter(i => i.quantity > 0)
                .map(i => ({
                    sku: i.sku,
                    quantity: i.quantity,
                    condition: i.condition,
                    reason: i.reason
                }));

            if (itemsToReturn.length === 0) {
                Swal.fire('Warning', 'Please select at least one item to return.', 'warning');
                setSubmitting(false);
                return;
            }

            await api.post(`/orders/${selectedOrder.id}/return`, {
                items: itemsToReturn,
                note: returnNote
            });

            Swal.fire('Success', 'Return processed successfully.', 'success');
            setShowReturnModal(false);
            fetchOrders(); // Refresh list
        } catch (err: unknown) {
            console.error("Return failed:", err);
            const message = (err as any).response?.data?.detail || 'Failed to process return.';
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
        >
            {error && <div className="alert alert-danger">{error}</div>}

            {/* Filters */}
            <div className="card mb-3 border-0 shadow-sm">
                <div className="card-body py-2">
                    {/* Channel Tabs */}
                    <ul className="nav nav-pills nav-fill mb-3">
                        {CHANNELS.map(ch => (
                            <li className="nav-item" key={ch.code}>
                                <button
                                    className={`nav-link ${channel === ch.code ? 'active' : ''}`}
                                    onClick={() => { setChannel(ch.code); setPage(1); }}
                                >
                                    {ch.badge && <span className={`badge bg-${ch.color} me-1`}>{ch.badge}</span>}
                                    {ch.label}
                                </button>
                            </li>
                        ))}
                    </ul>

                    {/* Search & Date Filters */}
                    <form onSubmit={handleSearch} className="row g-2 align-items-center">
                        <div className="col-md-3">
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={startDate}
                                onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
                                title="วันที่เริ่มต้น"
                            />
                        </div>
                        <div className="col-md-3">
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={endDate}
                                onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
                                title="วันที่สิ้นสุด"
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
                                <i className="bi bi-filter me-1"></i> กรอง
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            {/* Returns Table */}
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-3 py-3">รหัสออเดอร์</th>
                                    <th className="py-3">ช่องทาง</th>
                                    <th className="py-3">ลูกค้า</th>
                                    <th className="py-3">รายการสินค้า</th>
                                    <th className="py-3 text-end">ยอดเงินคืน</th>
                                    <th className="py-3">สถานะ</th>
                                    <th className="py-3">วันที่</th>
                                    <th className="pe-3 py-3" style={{ width: '80px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={8} className="text-center py-5 text-muted">
                                            <div className="spinner-border text-primary"></div>
                                            <div className="mt-2">กำลังโหลด...</div>
                                        </td>
                                    </tr>
                                ) : orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={8} className="text-center py-5 text-muted">
                                            <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                                            ไม่พบรายการสินค้าตีคืน
                                        </td>
                                    </tr>
                                ) : (
                                    orders.map((order) => (
                                        <tr key={order.id}>
                                            <td className="ps-3">
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
                                                {(order.items || []).map((item, i) => (
                                                    <div key={i} className="small text-truncate" style={{ maxWidth: '200px' }}>
                                                        {item.sku} x {item.quantity}
                                                    </div>
                                                ))}
                                            </td>
                                            <td className="text-end fw-bold text-danger">
                                                ฿{order.total_amount.toLocaleString()}
                                            </td>
                                            <td>{getStatusBadge(order.status_normalized)}</td>
                                            <td className="text-muted">
                                                <small>
                                                    {order.order_datetime
                                                        ? new Date(order.order_datetime).toLocaleDateString('th-TH')
                                                        : new Date(order.created_at).toLocaleDateString('th-TH')
                                                    }
                                                </small>
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
                                    <th style={{ width: '100px' }}>จำนวนที่ซื้อ</th>
                                    <th style={{ width: '100px' }}>จำนวนคืน</th>
                                    <th style={{ width: '150px' }}>สภาพสินค้า</th>
                                    <th>เหตุผล</th>
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
                                                <option value="DAMAGED">เสียหาย (Damaged)</option>
                                            </select>
                                        </td>
                                        <td>
                                            <input
                                                type="text"
                                                className="form-control form-control-sm"
                                                placeholder="ระบุเหตุผล..."
                                                value={item.reason}
                                                onChange={(e) => handleReturnItemChange(index, 'reason', e.target.value)}
                                                disabled={item.quantity === 0}
                                            />
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
