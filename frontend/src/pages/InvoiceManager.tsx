import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface InvoiceRequest {
    id: string;
    order_id: string;
    external_order_id: string | null;
    channel_code: string | null;
    invoice_name: string;
    tax_id: string;
    branch: string;
    profile_type: string;
    address: string;
    phone: string | null;
    email: string | null;
    status: string;
    invoice_number: string | null;
    invoice_date: string | null;
    created_at: string;
    order_total: number;
    rejected_reason: string | null;
}

interface Stats {
    pending: number;
    issued: number;
    rejected: number;
}

const InvoiceManager: React.FC = () => {
    const [requests, setRequests] = useState<InvoiceRequest[]>([]);
    const [stats, setStats] = useState<Stats>({ pending: 0, issued: 0, rejected: 0 });
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'PENDING' | 'ISSUED' | 'REJECTED' | ''>('PENDING');
    const [selectedRequest, setSelectedRequest] = useState<InvoiceRequest | null>(null);
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [processing, setProcessing] = useState(false);

    const fetchRequests = useCallback(async () => {
        setLoading(true);
        try {
            const params = filter ? `?status=${filter}` : '';
            const { data } = await api.get(`/finance/invoice-requests${params}`);
            setRequests(data.requests);
            setStats(data.counts);
        } catch (e) {
            console.error('Failed to fetch requests:', e);
        } finally {
            setLoading(false);
        }
    }, [filter]);

    useEffect(() => {
        fetchRequests();
    }, [fetchRequests]);

    const handleIssue = async (request: InvoiceRequest) => {
        if (!confirm(`ต้องการออกใบกำกับภาษีสำหรับ ${request.invoice_name} ใช่หรือไม่?`)) return;

        setProcessing(true);
        try {
            const { data } = await api.post(`/finance/invoice-requests/${request.id}/issue`);
            alert(`✅ ${data.message}`);
            fetchRequests();
        } catch (e: unknown) {
            const err = e as { response?: { data?: { detail?: string } } };
            alert(`❌ ${err.response?.data?.detail || 'เกิดข้อผิดพลาด'}`);
        } finally {
            setProcessing(false);
        }
    };

    const handleReject = async () => {
        if (!selectedRequest || !rejectReason.trim()) {
            alert('กรุณาระบุเหตุผล');
            return;
        }

        setProcessing(true);
        try {
            await api.post(`/finance/invoice-requests/${selectedRequest.id}/reject`, {
                reason: rejectReason.trim()
            });
            alert('✅ ปฏิเสธคำขอเรียบร้อยแล้ว');
            setShowRejectModal(false);
            setRejectReason('');
            setSelectedRequest(null);
            fetchRequests();
        } catch (e: unknown) {
            const err = e as { response?: { data?: { detail?: string } } };
            alert(`❌ ${err.response?.data?.detail || 'เกิดข้อผิดพลาด'}`);
        } finally {
            setProcessing(false);
        }
    };

    const getChannelBadge = (channel: string | null) => {
        const colors: Record<string, string> = {
            'tiktok': 'bg-dark',
            'shopee': 'bg-warning text-dark',
            'lazada': 'bg-primary',
            'manual': 'bg-secondary'
        };
        return colors[channel?.toLowerCase() || ''] || 'bg-secondary';
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item active">ใบกำกับภาษี</li>
        </>
    );

    return (
        <Layout title="จัดการใบกำกับภาษี" breadcrumb={breadcrumb}>
            {/* Stats Cards */}
            <div className="row g-3 mb-4">
                <div className="col-md-4">
                    <div
                        className={`card border-0 shadow-sm h-100 ${filter === 'PENDING' ? 'border-start border-4 border-warning' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setFilter('PENDING')}
                    >
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <div className="text-muted small">รอดำเนินการ</div>
                                    <div className="fs-2 fw-bold text-warning">{stats.pending}</div>
                                </div>
                                <div className="fs-1 text-warning opacity-50">⏳</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div
                        className={`card border-0 shadow-sm h-100 ${filter === 'ISSUED' ? 'border-start border-4 border-success' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setFilter('ISSUED')}
                    >
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <div className="text-muted small">ออกแล้ว</div>
                                    <div className="fs-2 fw-bold text-success">{stats.issued}</div>
                                </div>
                                <div className="fs-1 text-success opacity-50">✅</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div
                        className={`card border-0 shadow-sm h-100 ${filter === 'REJECTED' ? 'border-start border-4 border-danger' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setFilter('REJECTED')}
                    >
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <div className="text-muted small">ปฏิเสธ</div>
                                    <div className="fs-2 fw-bold text-danger">{stats.rejected}</div>
                                </div>
                                <div className="fs-1 text-danger opacity-50">❌</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Requests Table */}
            <div className="card border-0 shadow-sm">
                <div className="card-header bg-white d-flex justify-content-between align-items-center">
                    <span>
                        <i className="bi bi-receipt me-2"></i>
                        รายการขอใบกำกับภาษี
                        {filter && <span className="badge bg-secondary ms-2">{filter}</span>}
                    </span>
                    <button className="btn btn-sm btn-outline-secondary" onClick={fetchRequests}>
                        <i className="bi bi-arrow-clockwise me-1"></i> รีเฟรช
                    </button>
                </div>
                <div className="card-body p-0">
                    {loading ? (
                        <div className="text-center py-5">
                            <div className="spinner-border text-primary"></div>
                        </div>
                    ) : requests.length === 0 ? (
                        <div className="text-center py-5 text-muted">
                            <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                            ไม่มีรายการ
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-hover mb-0">
                                <thead className="bg-light">
                                    <tr>
                                        <th>Order</th>
                                        <th>ข้อมูลใบกำกับ</th>
                                        <th>ที่อยู่</th>
                                        <th className="text-end">ยอด</th>
                                        <th>วันที่ขอ</th>
                                        <th className="text-center">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {requests.map(req => (
                                        <tr key={req.id}>
                                            <td>
                                                <div className="fw-bold">{req.external_order_id || req.order_id.slice(0, 8)}</div>
                                                <span className={`badge ${getChannelBadge(req.channel_code)}`}>
                                                    {req.channel_code?.toUpperCase() || 'MANUAL'}
                                                </span>
                                            </td>
                                            <td>
                                                <div className="fw-semibold">{req.invoice_name}</div>
                                                <div className="small text-muted">
                                                    <i className="bi bi-building me-1"></i>
                                                    {req.tax_id}
                                                    {req.branch !== '00000' && <span className="ms-1">(สาขา {req.branch})</span>}
                                                </div>
                                                <span className={`badge ${req.profile_type === 'COMPANY' ? 'bg-info' : 'bg-secondary'}`}>
                                                    {req.profile_type === 'COMPANY' ? 'นิติบุคคล' : 'บุคคลธรรมดา'}
                                                </span>
                                            </td>
                                            <td>
                                                <div className="small" style={{ maxWidth: '200px' }}>{req.address}</div>
                                                {req.phone && <div className="small text-muted"><i className="bi bi-telephone me-1"></i>{req.phone}</div>}
                                            </td>
                                            <td className="text-end fw-bold">
                                                ฿{req.order_total.toLocaleString()}
                                            </td>
                                            <td>
                                                <div className="small">{req.created_at}</div>
                                            </td>
                                            <td className="text-center">
                                                {req.status === 'PENDING' && (
                                                    <div className="btn-group btn-group-sm">
                                                        <button
                                                            className="btn btn-success"
                                                            onClick={() => handleIssue(req)}
                                                            disabled={processing}
                                                        >
                                                            <i className="bi bi-check-lg me-1"></i>ออก
                                                        </button>
                                                        <button
                                                            className="btn btn-outline-danger"
                                                            onClick={() => {
                                                                setSelectedRequest(req);
                                                                setShowRejectModal(true);
                                                            }}
                                                            disabled={processing}
                                                        >
                                                            <i className="bi bi-x-lg"></i>
                                                        </button>
                                                    </div>
                                                )}
                                                {req.status === 'ISSUED' && (
                                                    <div>
                                                        <span className="badge bg-success mb-1">{req.invoice_number}</span>
                                                        <div className="small text-muted">{req.invoice_date}</div>
                                                        <a
                                                            href={`http://localhost:9202/api/orders/${req.order_id}/tax-invoice`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="btn btn-sm btn-outline-primary d-block mt-1"
                                                        >
                                                            <i className="bi bi-printer me-1"></i>พิมพ์
                                                        </a>
                                                    </div>
                                                )}
                                                {req.status === 'REJECTED' && (
                                                    <div>
                                                        <span className="badge bg-danger">ปฏิเสธ</span>
                                                        <div className="small text-muted">{req.rejected_reason}</div>
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* Reject Modal */}
            {showRejectModal && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-dialog-centered">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">ปฏิเสธคำขอใบกำกับภาษี</h5>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={() => setShowRejectModal(false)}
                                ></button>
                            </div>
                            <div className="modal-body">
                                <p>คำขอจาก: <strong>{selectedRequest?.invoice_name}</strong></p>
                                <label className="form-label">เหตุผลในการปฏิเสธ *</label>
                                <textarea
                                    className="form-control"
                                    rows={3}
                                    value={rejectReason}
                                    onChange={(e) => setRejectReason(e.target.value)}
                                    placeholder="เช่น ข้อมูลไม่ถูกต้อง, เลขผู้เสียภาษีไม่ตรงกับชื่อ"
                                ></textarea>
                            </div>
                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => setShowRejectModal(false)}
                                >
                                    ยกเลิก
                                </button>
                                <button
                                    type="button"
                                    className="btn btn-danger"
                                    onClick={handleReject}
                                    disabled={processing}
                                >
                                    {processing ? 'กำลังดำเนินการ...' : 'ยืนยันปฏิเสธ'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default InvoiceManager;
