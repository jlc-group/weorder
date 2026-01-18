import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import type { Order } from '../types';

interface FinanceSummary {
    today_revenue: number;
    today_gross_revenue: number;
    paid_today: number;
    pending_count: number;
    pending_amount: number;
}

const Finance: React.FC = () => {
    const [summary, setSummary] = useState<FinanceSummary | null>(null);
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);

    // Payment modal state
    const [showPaymentModal, setShowPaymentModal] = useState(false);
    const [selectedOrderId, setSelectedOrderId] = useState('');
    const [paymentAmount, setPaymentAmount] = useState(0);
    const [paymentMethod, setPaymentMethod] = useState('TRANSFER');
    const [paymentNote, setPaymentNote] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch finance summary
            try {
                const { data: summaryData } = await api.get('/finance/summary');
                setSummary(summaryData);
            } catch (e) {
                console.error('Failed to fetch finance summary:', e);
            }

            // Fetch orders with NEW status (pending payment)
            const { data: ordersData } = await api.get('/orders?status=NEW&per_page=100');
            setOrders(ordersData.orders || []);
        } catch (e) {
            console.error('Failed to fetch data:', e);
        } finally {
            setLoading(false);
        }
    };

    const openPaymentModal = (orderId: string, amount: number) => {
        setSelectedOrderId(orderId);
        setPaymentAmount(amount);
        setPaymentMethod('TRANSFER');
        setPaymentNote('');
        setShowPaymentModal(true);
    };

    const savePayment = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);

        try {
            await api.post('/payments', {
                order_id: selectedOrderId,
                amount: paymentAmount,
                payment_method: paymentMethod,
                note: paymentNote
            });

            setShowPaymentModal(false);
            fetchData();
        } catch (e) {
            console.error('Failed to save payment:', e);
            alert('เกิดข้อผิดพลาดในการบันทึก');
        } finally {
            setSaving(false);
        }
    };

    const getChannelBadge = (channel: string) => {
        const colors: Record<string, string> = {
            'tiktok': 'bg-dark',
            'shopee': 'bg-warning text-dark',
            'lazada': 'bg-primary',
        };
        return <span className={`badge ${colors[channel] || 'bg-secondary'}`}>{channel}</span>;
    };

    const breadcrumb = <li className="breadcrumb-item active">Finance</li>;

    // Calculate totals from orders
    const pendingAmount = orders.reduce((sum, o) => sum + (o.total_amount || 0), 0);

    return (
        <Layout
            title="การเงิน"
            breadcrumb={breadcrumb}
            actions={
                <button
                    className="btn btn-success"
                    onClick={() => {
                        if (orders.length > 0) {
                            openPaymentModal(orders[0].id, orders[0].total_amount);
                        } else {
                            setShowPaymentModal(true);
                        }
                    }}
                >
                    <i className="bi bi-cash-coin me-1"></i> บันทึกรับชำระ
                </button>
            }
        >
            {/* Stats */}
            <div className="row g-3 mb-4">
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body text-center">
                            <div className="fs-4 fw-bold text-warning">
                                ฿{loading ? '...' : pendingAmount.toLocaleString()}
                            </div>
                            <div className="small text-muted">รอชำระ</div>
                        </div>
                    </div>
                </div>
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body text-center">
                            <div className="fs-4 fw-bold text-success">
                                ฿{loading ? '...' : (summary?.today_gross_revenue?.toLocaleString() || '0')}
                            </div>
                            <div className="small text-muted" title="ยอดขายรวมส่วนลด Platform (ใช้สำหรับภาษีขาย)">
                                รายได้รวม (Tax Base)
                            </div>
                            {summary?.today_revenue !== summary?.today_gross_revenue && (
                                <div className="text-muted extra-small" style={{ fontSize: '0.7rem' }}>
                                    (ลูกค้าจ่าย: ฿{(summary?.today_revenue || 0).toLocaleString()})
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body text-center">
                            <div className="fs-4 fw-bold text-primary">
                                {loading ? '...' : orders.length}
                            </div>
                            <div className="small text-muted">ออเดอร์รอชำระ</div>
                        </div>
                    </div>
                </div>
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body text-center">
                            <div className="fs-4 fw-bold text-info">
                                {loading ? '...' : (summary?.paid_today || 0)}
                            </div>
                            <div className="small text-muted">ชำระแล้ววันนี้</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Orders with Payment Status */}
            <div className="card border-0 shadow-sm">
                <div className="card-header bg-white">
                    <i className="bi bi-receipt me-2"></i>ออเดอร์รอชำระ
                </div>
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th>รหัสออเดอร์</th>
                                    <th>ลูกค้า</th>
                                    <th>ช่องทาง</th>
                                    <th className="text-end">ยอดรวม</th>
                                    <th className="text-end">ชำระแล้ว</th>
                                    <th className="text-end">คงค้าง</th>
                                    <th>สถานะ</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr>
                                        <td colSpan={8} className="text-center py-5">
                                            <div className="spinner-border text-primary"></div>
                                            <div className="mt-2">กำลังโหลด...</div>
                                        </td>
                                    </tr>
                                ) : orders.length === 0 ? (
                                    <tr>
                                        <td colSpan={8} className="text-center text-muted py-5">
                                            <i className="bi bi-check-circle fs-1 d-block mb-2 text-success"></i>
                                            ไม่มีออเดอร์รอชำระ
                                        </td>
                                    </tr>
                                ) : (
                                    orders.map(order => {
                                        const paid = (order as any).paid_amount || 0;
                                        const pending = (order.total_amount || 0) - paid;

                                        return (
                                            <tr key={order.id}>
                                                <td>
                                                    <a href={`/orders/${order.id}`} className="fw-semibold text-decoration-none">
                                                        {order.external_order_id || order.id.slice(0, 8)}
                                                    </a>
                                                </td>
                                                <td>{order.customer_name || '-'}</td>
                                                <td>{getChannelBadge(order.channel_code)}</td>
                                                <td className="text-end fw-mono">฿{order.total_amount.toLocaleString()}</td>
                                                <td className="text-end fw-mono text-success">฿{paid.toLocaleString()}</td>
                                                <td className="text-end fw-mono text-danger">฿{pending.toLocaleString()}</td>
                                                <td>
                                                    <span className="badge bg-warning text-dark">
                                                        {order.payment_status || 'PENDING'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        className="btn btn-sm btn-outline-success"
                                                        onClick={() => openPaymentModal(order.id, pending)}
                                                    >
                                                        <i className="bi bi-cash"></i>
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Payment Modal */}
            {showPaymentModal && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">บันทึกรับชำระ</h5>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={() => setShowPaymentModal(false)}
                                />
                            </div>
                            <form onSubmit={savePayment}>
                                <div className="modal-body">
                                    <div className="mb-3">
                                        <label className="form-label">ออเดอร์</label>
                                        <select
                                            className="form-select"
                                            value={selectedOrderId}
                                            onChange={(e) => {
                                                setSelectedOrderId(e.target.value);
                                                const order = orders.find(o => o.id === e.target.value);
                                                if (order) setPaymentAmount(order.total_amount);
                                            }}
                                            required
                                        >
                                            <option value="">เลือกออเดอร์...</option>
                                            {orders.map(o => (
                                                <option key={o.id} value={o.id}>
                                                    {o.external_order_id || o.id.slice(0, 8)} - ฿{o.total_amount.toLocaleString()}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">จำนวนเงิน</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={paymentAmount}
                                            onChange={(e) => setPaymentAmount(parseFloat(e.target.value) || 0)}
                                            step="0.01"
                                            required
                                        />
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">วิธีชำระ</label>
                                        <select
                                            className="form-select"
                                            value={paymentMethod}
                                            onChange={(e) => setPaymentMethod(e.target.value)}
                                        >
                                            <option value="TRANSFER">โอนเงิน</option>
                                            <option value="CASH">เงินสด</option>
                                            <option value="COD">COD</option>
                                        </select>
                                    </div>
                                    <div className="mb-3">
                                        <label className="form-label">หมายเหตุ</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={paymentNote}
                                            onChange={(e) => setPaymentNote(e.target.value)}
                                        />
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button
                                        type="button"
                                        className="btn btn-secondary"
                                        onClick={() => setShowPaymentModal(false)}
                                    >
                                        ยกเลิก
                                    </button>
                                    <button
                                        type="submit"
                                        className="btn btn-success"
                                        disabled={saving}
                                    >
                                        {saving ? (
                                            <><span className="spinner-border spinner-border-sm me-1"></span> กำลังบันทึก...</>
                                        ) : (
                                            <><i className="bi bi-check-circle me-1"></i> บันทึก</>
                                        )}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Finance;
