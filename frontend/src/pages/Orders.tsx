import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import Layout from '../components/Layout';
import type { Order } from '../types';

const CHANNELS = [
    { code: 'all', label: 'ทั้งหมด', badge: '' },
    { code: 'shopee', label: 'Shopee', badge: 'S', color: 'warning' },
    { code: 'lazada', label: 'Lazada', badge: 'L', color: 'primary' },
    { code: 'tiktok', label: 'TikTok', badge: 'T', color: 'dark' },
    { code: 'facebook', label: 'Facebook', badge: 'F', color: 'info' },
    { code: 'manual', label: 'Manual', badge: 'M', color: 'secondary' },
];

const STATUSES = [
    { value: 'all', label: 'ทุกสถานะ' },
    { value: 'NEW', label: 'NEW - ใหม่' },
    { value: 'PAID', label: 'PAID - ชำระแล้ว' },
    { value: 'READY_TO_SHIP', label: 'READY TO SHIP - แพ็คแล้ว' },
    { value: 'PACKING', label: 'PACKING - กำลังแพ็ค' },
    { value: 'SHIPPED', label: 'SHIPPED - จัดส่งแล้ว' },
    { value: 'DELIVERED', label: 'DELIVERED - ส่งถึงแล้ว' },
    { value: 'CANCELLED', label: 'CANCELLED - ยกเลิก' },
];

const Orders: React.FC = () => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [channel, setChannel] = useState('all');
    const [status, setStatus] = useState('all');
    const [search, setSearch] = useState('');
    const [startDate, setStartDate] = useState(() => {
        // Default to today
        const today = new Date();
        return today.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => {
        // Default to today
        const today = new Date();
        return today.toISOString().split('T')[0];
    });
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [perPage] = useState(20);

    // Bulk selection
    const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());

    const fetchOrders = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: perPage.toString(),
            });
            if (channel !== 'all') params.set('channel', channel);
            if (status !== 'all') params.set('status', status);
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
            console.error("Failed to fetch orders:", err);
            setError("Failed to load orders");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOrders();
    }, [channel, status, page, startDate, endDate]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        fetchOrders();
    };

    const toggleOrder = (id: string) => {
        const newSet = new Set(selectedOrders);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        setSelectedOrders(newSet);
    };

    const toggleAll = (checked: boolean) => {
        if (checked) {
            setSelectedOrders(new Set(orders.map(o => o.id)));
        } else {
            setSelectedOrders(new Set());
        }
    };

    const printLabels = () => {
        const ids = Array.from(selectedOrders).join(',');
        window.open(`/packing/print?ids=${ids}`, '_blank');
    };

    const updateBulkStatus = async (newStatus: string) => {
        if (!confirm(`เปลี่ยนสถานะ ${selectedOrders.size} รายการเป็น ${newStatus}?`)) return;

        try {
            for (const id of selectedOrders) {
                await api.post(`/orders/${id}/status`, { status: newStatus });
            }
            setSelectedOrders(new Set());
            fetchOrders();
        } catch (e) {
            console.error('Bulk status update failed:', e);
            alert('เกิดข้อผิดพลาด');
        }
    };

    const getStatusBadge = (status: string) => {
        const classes: Record<string, string> = {
            'NEW': 'bg-secondary',
            'PAID': 'bg-success',
            'PACKING': 'bg-warning text-dark',
            'SHIPPED': 'bg-info text-dark',
            'DELIVERED': 'bg-primary',
            'CANCELLED': 'bg-danger',
        };
        return <span className={`badge ${classes[status] || 'bg-secondary'}`}>{status}</span>;
    };

    const getChannelBadge = (channelCode: string) => {
        const ch = CHANNELS.find(c => c.code === channelCode);
        if (!ch || !ch.badge) return <span className="badge bg-light text-dark border">{channelCode}</span>;
        return <span className={`badge bg-${ch.color}`}>{channelCode}</span>;
    };

    const totalPages = Math.ceil(total / perPage);

    const breadcrumb = (
        <li className="breadcrumb-item active" aria-current="page">Orders</li>
    );

    const [syncing, setSyncing] = useState(false);

    // ... (existing code)

    const handleSync = async () => {
        if (syncing) return;
        setSyncing(true);
        try {
            await api.post('/sync/trigger');
            // Poll status
            const interval = setInterval(async () => {
                const res = await api.get('/sync/status');
                if (!res.data.is_running) {
                    clearInterval(interval);
                    setSyncing(false);
                    fetchOrders(); // Refresh list
                    alert('Sync Completed!');
                }
            }, 2000);
        } catch (e) {
            console.error(e);
            setSyncing(false);
            alert('Sync Trigger Failed');
        }
    };

    // ... (existing code)

    return (
        <Layout
            title="จัดการออเดอร์"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <button
                        className={`btn btn-${syncing ? 'secondary' : 'success'}`}
                        onClick={handleSync}
                        disabled={syncing}
                    >
                        <i className={`bi bi-${syncing ? 'hourglass-split' : 'arrow-repeat'} me-1 ${syncing ? 'fa-spin' : ''}`}></i>
                        {syncing ? 'Syncing...' : 'Sync Orders'}
                    </button>
                    <Link to="/orders/create" className="btn btn-primary">
                        <i className="bi bi-plus-circle me-1"></i> สร้างออเดอร์
                    </Link>
                </div>
            }
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

                    {/* Status & Search & Date Filters */}
                    <form onSubmit={handleSearch} className="row g-2 align-items-center">
                        <div className="col-md-2">
                            <select
                                className="form-select form-select-sm"
                                value={status}
                                onChange={(e) => { setStatus(e.target.value); setPage(1); }}
                            >
                                {STATUSES.map(s => (
                                    <option key={s.value} value={s.value}>{s.label}</option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-2">
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={startDate}
                                onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
                                title="วันที่เริ่มต้น"
                            />
                        </div>
                        <div className="col-md-2">
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={endDate}
                                onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
                                title="วันที่สิ้นสุด"
                            />
                        </div>
                        <div className="col-md-3">
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
                        <div className="col-md-1">
                            <button type="submit" className="btn btn-primary btn-sm w-100">
                                <i className="bi bi-filter me-1"></i> กรอง
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            {/* Orders Table */}
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-3" style={{ width: '40px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            checked={selectedOrders.size === orders.length && orders.length > 0}
                                            onChange={(e) => toggleAll(e.target.checked)}
                                        />
                                    </th>
                                    <th className="py-3">รหัสออเดอร์</th>
                                    <th className="py-3">ช่องทาง</th>
                                    <th className="py-3">ลูกค้า</th>
                                    <th className="py-3">รายการ</th>
                                    <th className="py-3 text-end">ยอดรวม</th>
                                    <th className="py-3">สถานะ</th>
                                    <th className="py-3">วันที่</th>
                                    <th className="pe-3 py-3" style={{ width: '120px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={9} className="text-center py-5 text-muted">
                                            <div className="spinner-border text-primary"></div>
                                            <div className="mt-2">กำลังโหลด...</div>
                                        </td>
                                    </tr>
                                ) : orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={9} className="text-center py-5 text-muted">
                                            <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                                            ไม่พบออเดอร์
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
                                                    onChange={() => toggleOrder(order.id)}
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
                                                <small className="text-muted">{order.items?.length || 0} รายการ</small>
                                            </td>
                                            <td className="text-end fw-bold">
                                                ฿{order.total_amount.toLocaleString()}
                                            </td>
                                            <td>{getStatusBadge(order.status_normalized)}</td>
                                            <td className="text-muted">
                                                <small>
                                                    {order.order_datetime
                                                        ? new Date(order.order_datetime).toLocaleDateString('th-TH')
                                                        : order.created_at
                                                            ? new Date(order.created_at).toLocaleDateString('th-TH')
                                                            : '-'
                                                    }
                                                </small>
                                            </td>
                                            <td className="pe-3">
                                                <div className="btn-group btn-group-sm">
                                                    <Link to={`/orders/${order.id}`} className="btn btn-outline-primary" title="ดูรายละเอียด">
                                                        <i className="bi bi-eye"></i>
                                                    </Link>
                                                    <Link to={`/orders/${order.id}/edit`} className="btn btn-outline-secondary" title="แก้ไข">
                                                        <i className="bi bi-pencil"></i>
                                                    </Link>
                                                </div>
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

            {/* Bulk Actions */}
            {selectedOrders.size > 0 && (
                <div className="position-fixed bottom-0 start-50 translate-middle-x mb-4" style={{ zIndex: 1050 }}>
                    <div className="card shadow-lg border-primary">
                        <div className="card-body py-2 px-3 d-flex align-items-center gap-3">
                            <span className="text-primary fw-semibold">
                                {selectedOrders.size} รายการที่เลือก
                            </span>
                            <button className="btn btn-sm btn-outline-primary" onClick={printLabels}>
                                <i className="bi bi-printer me-1"></i> พิมพ์ใบปะหน้า
                            </button>
                            <button className="btn btn-sm btn-outline-warning" onClick={() => updateBulkStatus('PACKING')}>
                                <i className="bi bi-box2 me-1"></i> เปลี่ยนเป็น PACKING
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Orders;
