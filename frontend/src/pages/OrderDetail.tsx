import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import type { Order } from '../types';

const OrderDetail: React.FC = () => {
    const { orderId } = useParams<{ orderId: string }>();
    const [order, setOrder] = useState<Order | null>(null);
    const [loading, setLoading] = useState(true);
    const [profitBreakdown, setProfitBreakdown] = useState<any>(null);

    const fetchOrder = useCallback(async () => {
        try {
            const { data } = await api.get(`/orders/${orderId}`);
            setOrder(data);

            // Also fetch profit breakdown if order exists
            try {
                const { data: profitData } = await api.get(`/finance/profit/${orderId}`);
                setProfitBreakdown(profitData);
            } catch (e) {
                console.error('Failed to fetch profit breakdown:', e);
            }
        } catch (e) {
            console.error('Failed to fetch order:', e);
        } finally {
            setLoading(false);
        }
    }, [orderId]);

    useEffect(() => {
        if (orderId) {
            fetchOrder();
        }
    }, [orderId, fetchOrder]);

    const changeStatus = async (newStatus: string) => {
        if (!confirm(`ต้องการเปลี่ยนสถานะเป็น ${newStatus} ใช่หรือไม่?`)) return;

        try {
            await api.post(`/orders/${orderId}/status`, { status: newStatus });
            fetchOrder();
        } catch (e) {
            console.error('Failed to change status:', e);
            alert('ไม่สามารถเปลี่ยนสถานะได้');
        }
    };

    const getStatusTransitions = (currentStatus: string): string[] => {
        const transitions: Record<string, string[]> = {
            'NEW': ['PAID', 'CANCELLED'],
            'PAID': ['PACKING', 'CANCELLED'],
            'PACKING': ['SHIPPED'],
            'SHIPPED': ['DELIVERED', 'RETURNED'],
            'DELIVERED': ['RETURNED'],
            'RETURNED': [],
            'CANCELLED': []
        };
        return transitions[currentStatus] || [];
    };

    const getStatusButtonClass = (status: string): string => {
        const classes: Record<string, string> = {
            'PAID': 'btn-success',
            'PACKING': 'btn-warning',
            'SHIPPED': 'btn-info',
            'DELIVERED': 'btn-success',
            'CANCELLED': 'btn-danger',
            'RETURNED': 'btn-secondary'
        };
        return classes[status] || 'btn-outline-primary';
    };

    const getStatusBadgeClass = (status: string): string => {
        const classes: Record<string, string> = {
            'NEW': 'bg-secondary',
            'PAID': 'bg-success',
            'PACKING': 'bg-warning text-dark',
            'SHIPPED': 'bg-info text-dark',
            'DELIVERED': 'bg-primary',
            'CANCELLED': 'bg-danger',
            'RETURNED': 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    };

    const printLabel = () => {
        window.open(`/api/orders/${orderId}/label`, '_blank');
    };

    const printTaxInvoice = () => {
        window.open(`/api/orders/${orderId}/tax-invoice`, '_blank');
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item"><a href="/orders" className="text-decoration-none">Orders</a></li>
            <li className="breadcrumb-item active">รายละเอียด</li>
        </>
    );

    if (loading) {
        return (
            <Layout title="โหลด..." breadcrumb={breadcrumb}>
                <div className="text-center py-5">
                    <div className="spinner-border text-primary"></div>
                </div>
            </Layout>
        );
    }

    if (!order) {
        return (
            <Layout title="ไม่พบออเดอร์" breadcrumb={breadcrumb}>
                <div className="text-center py-5 text-muted">
                    <i className="bi bi-exclamation-circle fs-1 d-block mb-2"></i>
                    ไม่พบออเดอร์ที่ระบุ
                </div>
            </Layout>
        );
    }

    const allowedTransitions = getStatusTransitions(order.status_normalized);

    return (
        <Layout
            title={order.external_order_id || order.id.substring(0, 8)}
            breadcrumb={breadcrumb}
            actions={
                <>
                    <a href={`/orders/${order.id}/edit`} className="btn btn-outline-primary me-2">
                        <i className="bi bi-pencil me-1"></i> แก้ไข
                    </a>
                    <button className="btn btn-outline-secondary me-2" onClick={printLabel}>
                        <i className="bi bi-printer me-1"></i> พิมพ์ใบปะหน้า
                    </button>
                    {['DELIVERED', 'COMPLETED'].includes(order.status_normalized) && (
                        <button className="btn btn-outline-success" onClick={printTaxInvoice}>
                            <i className="bi bi-receipt me-1"></i> ใบกำกับภาษี
                        </button>
                    )}
                </>
            }
        >
            <div className="row g-3">
                {/* Order Info */}
                <div className="col-lg-8">
                    <div className="card mb-3 border-0 shadow-sm">
                        <div className="card-header bg-white d-flex justify-content-between align-items-center">
                            <span><i className="bi bi-info-circle me-2"></i>ข้อมูลออเดอร์</span>
                            <span className={`badge ${getStatusBadgeClass(order.status_normalized)}`}>
                                {order.status_normalized}
                            </span>
                        </div>
                        <div className="card-body">
                            <div className="row g-3">
                                <div className="col-md-4">
                                    <label className="form-label text-muted">รหัสออเดอร์</label>
                                    <div className="fw-bold">{order.external_order_id || order.id}</div>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label text-muted">ช่องทาง</label>
                                    <div>
                                        <span className={`badge bg-${order.channel_code === 'tiktok' ? 'dark' : 'secondary'}`}>
                                            {order.channel_code}
                                        </span>
                                    </div>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label text-muted">วันที่สร้าง</label>
                                    <div>
                                        {order.order_datetime
                                            ? new Date(order.order_datetime).toLocaleString('th-TH')
                                            : order.created_at
                                                ? new Date(order.created_at).toLocaleString('th-TH')
                                                : '-'
                                        }
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Customer Info */}
                    <div className="card mb-3 border-0 shadow-sm">
                        <div className="card-header bg-white">
                            <i className="bi bi-person me-2"></i>ข้อมูลลูกค้า
                        </div>
                        <div className="card-body">
                            <div className="row g-3">
                                <div className="col-md-6">
                                    <label className="form-label text-muted">ชื่อ</label>
                                    <div className="fw-semibold">{order.customer_name || '-'}</div>
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label text-muted">เบอร์โทร</label>
                                    <div>{order.customer_phone || '-'}</div>
                                </div>
                                <div className="col-12">
                                    <label className="form-label text-muted">ที่อยู่จัดส่ง</label>
                                    <div>{order.customer_address || '-'}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Order Items */}
                    <div className="card border-0 shadow-sm">
                        <div className="card-header bg-white">
                            <i className="bi bi-cart me-2"></i>รายการสินค้า
                        </div>
                        <div className="card-body p-0">
                            <table className="table mb-0">
                                <thead className="bg-light">
                                    <tr>
                                        <th>SKU</th>
                                        <th>ชื่อสินค้า</th>
                                        <th className="text-center">จำนวน</th>
                                        <th className="text-end">ราคา/หน่วย</th>
                                        <th className="text-end">รวม</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {order.items && order.items.length > 0 ? (
                                        order.items.map(item => (
                                            <tr key={item.id}>
                                                <td className="fw-mono">{item.sku}</td>
                                                <td>
                                                    {item.product_name}
                                                    {item.line_type !== 'NORMAL' && (
                                                        <span className="badge bg-info ms-1">{item.line_type}</span>
                                                    )}
                                                </td>
                                                <td className="text-center">{item.quantity}</td>
                                                <td className="text-end">฿{item.unit_price.toLocaleString()}</td>
                                                <td className="text-end fw-bold">฿{item.line_total.toLocaleString()}</td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan={5} className="text-center text-muted">ไม่มีรายการ</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Financial Transparency (Money Trail) */}
                    {profitBreakdown && (
                        <div className="card mt-3 border-0 shadow-sm overflow-hidden">
                            <div className="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                                <span><i className="bi bi-cash-coin me-2"></i>เส้นทางการเงิน (Money Trail)</span>
                                <span className="small opacity-75">ข้อมูลลึกจากแพลตฟอร์ม</span>
                            </div>
                            <div className="card-body p-0">
                                <div className="p-3 bg-light border-bottom">
                                    <div className="row text-center">
                                        <div className="col border-end">
                                            <div className="small text-muted">ลูกค้าชำระ</div>
                                            <div className="fw-bold text-dark">฿{(profitBreakdown.revenue?.total_gross_revenue || 0).toLocaleString()}</div>
                                        </div>
                                        <div className="col border-end">
                                            <div className="small text-muted">ค่าธรรมเนียมรวม</div>
                                            <div className="fw-bold text-danger">฿{(profitBreakdown.total_deductions || 0).toLocaleString()}</div>
                                        </div>
                                        <div className="col">
                                            <div className="small text-muted">เงินโอนเข้าสุทธิ</div>
                                            <div className="fw-bold text-success fs-5">฿{(profitBreakdown.net_income || 0).toLocaleString()}</div>
                                        </div>
                                    </div>
                                </div>
                                <div className="table-responsive">
                                    <table className="table table-sm table-hover mb-0">
                                        <thead>
                                            <tr className="bg-white">
                                                <th className="ps-3 py-2">ประเภทรายได้/ค่าธรรมเนียม</th>
                                                <th className="py-2">รายละเอียด</th>
                                                <th className="text-end pe-3 py-2">จำนวนเงิน</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr className="table-success">
                                                <td className="ps-3 fw-bold">รายรับรวม (Revenue + Plat. Discount)</td>
                                                <td className="small">ยอดขายรวมที่แพลตฟอร์มรับมา</td>
                                                <td className="text-end pe-3 fw-bold text-success">฿{(profitBreakdown.revenue?.total_gross_revenue || 0).toLocaleString()}</td>
                                            </tr>
                                            {profitBreakdown.deductions?.map((d: any, idx: number) => (
                                                <tr key={idx}>
                                                    <td className="ps-3 text-muted">{d.type}</td>
                                                    <td className="small">{d.description}</td>
                                                    <td className="text-end pe-3 text-danger">฿{d.amount.toLocaleString()}</td>
                                                </tr>
                                            ))}
                                            <tr className="border-top-2 fw-bold bg-light">
                                                <td colSpan={2} className="ps-3 py-2">เงินโอนเข้าจริง (Actual Settlement)</td>
                                                <td className="text-end pe-3 py-2 text-primary fs-6">฿{(profitBreakdown.net_income || 0).toLocaleString()}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Summary Sidebar */}
                <div className="col-lg-4">
                    <div className="card mb-3 border-0 shadow-sm">
                        <div className="card-header bg-white">
                            <i className="bi bi-calculator me-2"></i>สรุปยอด
                        </div>
                        <div className="card-body">
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">ราคารวม</span>
                                <span>฿{(order.subtotal_amount || 0).toLocaleString()}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">ส่วนลด</span>
                                <span className="text-danger">-฿{(order.discount_amount || 0).toLocaleString()}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">ค่าจัดส่ง</span>
                                <span>฿{(order.shipping_fee || 0).toLocaleString()}</span>
                            </div>
                            <hr />
                            <div className="d-flex justify-content-between fs-5 fw-bold">
                                <span>ยอดรวมสุทธิ</span>
                                <span className="text-primary">฿{order.total_amount.toLocaleString()}</span>
                            </div>
                        </div>
                    </div>

                    {/* Payment Status */}
                    <div className="card mb-3 border-0 shadow-sm">
                        <div className="card-header bg-white">
                            <i className="bi bi-credit-card me-2"></i>การชำระเงิน
                        </div>
                        <div className="card-body">
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">วิธีชำระ</span>
                                <span>{order.payment_method || '-'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">สถานะ</span>
                                <span className={`badge ${order.payment_status === 'PAID' ? 'bg-success' : 'bg-warning text-dark'}`}>
                                    {order.payment_status || 'PENDING'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Status Actions */}
                    <div className="card border-0 shadow-sm">
                        <div className="card-header bg-white">
                            <i className="bi bi-arrow-right-circle me-2"></i>เปลี่ยนสถานะ
                        </div>
                        <div className="card-body">
                            {allowedTransitions.length === 0 ? (
                                <div className="text-muted text-center">ไม่สามารถเปลี่ยนสถานะได้</div>
                            ) : (
                                allowedTransitions.map(status => (
                                    <button
                                        key={status}
                                        className={`btn ${getStatusButtonClass(status)} w-100 mb-2`}
                                        onClick={() => changeStatus(status)}
                                    >
                                        {status}
                                    </button>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default OrderDetail;
