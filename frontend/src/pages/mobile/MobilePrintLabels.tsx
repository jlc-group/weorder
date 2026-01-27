import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import './Mobile.css';

interface CourierSummary {
    courier_code: string;
    courier_name: string;
    count: number;
}

interface BatchFile {
    page: number;
    url: string;
    orders: number;
}

interface PlatformSummary {
    channel: string;
    channel_name: string;
    count: number;
}

interface PrintBatchResponse {
    courier: string;
    total_orders: number;
    total_files: number;
    files: BatchFile[];
}

const MobilePrintLabels: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [couriers, setCouriers] = useState<CourierSummary[]>([]);
    const [totalOrders, setTotalOrders] = useState(0);
    const [selectedCourier, setSelectedCourier] = useState<string | null>(null);
    const [batchInfo, setBatchInfo] = useState<PrintBatchResponse | null>(null);
    const [downloading, setDownloading] = useState<number | null>(null);
    const [status, setStatus] = useState('READY_TO_SHIP');
    const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
    const [selectedPlatform, setSelectedPlatform] = useState<string>('');
    const batchSize = 50; // Reduced for reliability

    // Load platform summary
    useEffect(() => {
        loadPlatformSummary();
    }, [status]);

    // Load courier summary when platform changes
    useEffect(() => {
        loadCourierSummary();
    }, [status, selectedPlatform]);

    const loadPlatformSummary = async () => {
        try {
            const { data } = await api.get('/labels/platform-summary', {
                params: { status }
            });
            setPlatforms(data.platforms || []);
        } catch (err) {
            console.error('Error loading platform summary:', err);
        }
    };

    const loadCourierSummary = async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = { status };
            if (selectedPlatform) {
                params.channel = selectedPlatform;
            }
            const { data } = await api.get('/labels/courier-summary', { params });
            setCouriers(data.couriers || []);
            setTotalOrders(data.total || 0);
        } catch (err) {
            console.error('Error loading courier summary:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSelectCourier = async (courierCode: string) => {
        setSelectedCourier(courierCode);
        try {
            const { data } = await api.post('/labels/print-batch', {
                courier: courierCode,
                status,
                channel: selectedPlatform || null,
                max_per_file: batchSize,
                sort_by_sku: true
            });
            setBatchInfo(data);
        } catch (err) {
            console.error('Error getting batch info:', err);
        }
    };

    const handleDownloadFile = async (file: BatchFile, index: number) => {
        setDownloading(index);
        try {
            // Open PDF in new tab
            let url = `/api/labels/by-courier?courier=${encodeURIComponent(selectedCourier || '')}&status=${status}&page=${file.page}&per_page=${batchSize}&sort_by_sku=true`;
            if (selectedPlatform) {
                url += `&channel=${selectedPlatform}`;
            }
            window.open(url, '_blank');
        } catch (err) {
            console.error('Download error:', err);
        } finally {
            setTimeout(() => setDownloading(null), 1000);
        }
    };

    const handleDownloadAll = async () => {
        if (!batchInfo) return;

        for (let i = 0; i < batchInfo.files.length; i++) {
            await handleDownloadFile(batchInfo.files[i], i);
            // Delay between downloads to prevent browser blocking
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    };

    return (
        <div className="mobile-container">
            {/* Header */}
            <div className="mobile-header">
                <button
                    className="mobile-header-back"
                    onClick={() => selectedCourier ? (setSelectedCourier(null), setBatchInfo(null)) : navigate('/mobile')}
                >
                    <i className="bi bi-chevron-left"></i>
                </button>
                <h1 className="mobile-header-title">
                    <i className="bi bi-printer-fill me-2" style={{ color: '#6366f1' }}></i>
                    Print Labels
                </h1>
                <button
                    className="mobile-header-action"
                    onClick={loadCourierSummary}
                    style={{ background: 'transparent', border: 'none', color: 'white', fontSize: '1.2rem' }}
                >
                    <i className="bi bi-arrow-clockwise"></i>
                </button>
            </div>

            {/* Status Filter */}
            <div style={{ padding: '0 16px', marginBottom: 16 }}>
                <div className="btn-group w-100" role="group">
                    <button
                        className={`btn ${status === 'READY_TO_SHIP' ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => setStatus('READY_TO_SHIP')}
                    >
                        รอจัดส่ง
                    </button>
                    <button
                        className={`btn ${status === 'PAID' ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => setStatus('PAID')}
                    >
                        รอแพ็ค
                    </button>
                </div>
            </div>

            {/* Platform Filter */}
            <div style={{ padding: '0 16px', marginBottom: 16 }}>
                <div style={{
                    display: 'flex',
                    gap: 8,
                    overflowX: 'auto',
                    paddingBottom: 4
                }}>
                    {/* All Platforms */}
                    <button
                        className={`btn ${selectedPlatform === '' ? 'btn-dark' : 'btn-outline-secondary'}`}
                        onClick={() => setSelectedPlatform('')}
                        style={{ whiteSpace: 'nowrap', minWidth: 'fit-content' }}
                    >
                        ทั้งหมด
                    </button>
                    {/* Platform buttons */}
                    {platforms.map(p => (
                        <button
                            key={p.channel}
                            className={`btn ${selectedPlatform === p.channel ? 'btn-dark' : 'btn-outline-secondary'}`}
                            onClick={() => setSelectedPlatform(p.channel)}
                            style={{
                                whiteSpace: 'nowrap',
                                minWidth: 'fit-content',
                                backgroundColor: selectedPlatform === p.channel ?
                                    (p.channel === 'tiktok' ? '#000' : p.channel === 'shopee' ? '#ee4d2d' : p.channel === 'lazada' ? '#0f146d' : '#333')
                                    : undefined,
                                borderColor: selectedPlatform === p.channel ? 'transparent' : undefined
                            }}
                        >
                            {p.channel_name} ({p.count.toLocaleString()})
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="mobile-empty" style={{ padding: 48 }}>
                    <div className="spinner-border text-primary"></div>
                    <p style={{ marginTop: 16 }}>กำลังโหลด...</p>
                </div>
            ) : !selectedCourier ? (
                /* Courier Selection */
                <>
                    <div style={{ padding: '0 16px', marginBottom: 16 }}>
                        <div className="mobile-card" style={{
                            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                            color: 'white',
                            textAlign: 'center',
                            padding: 24
                        }}>
                            <div style={{ fontSize: '2.5rem', fontWeight: 700 }}>{totalOrders.toLocaleString()}</div>
                            <div style={{ opacity: 0.9, fontSize: '0.95rem' }}>
                                <i className="bi bi-box-seam me-1"></i>
                                Orders {selectedPlatform ? `(${selectedPlatform.toUpperCase()})` : '(ทั้งหมด)'} - {status === 'READY_TO_SHIP' ? 'RTS' : 'PAID'}
                            </div>
                        </div>
                    </div>

                    <div style={{ padding: '0 16px' }}>
                        <h5 style={{ marginBottom: 12, fontWeight: 600 }}>
                            <i className="bi bi-truck me-2"></i>
                            เลือกขนส่ง
                        </h5>

                        {couriers.length === 0 ? (
                            <div className="mobile-empty" style={{ padding: 32 }}>
                                <i className="bi bi-inbox" style={{ fontSize: '2rem', opacity: 0.5 }}></i>
                                <p style={{ marginTop: 12, opacity: 0.7 }}>ไม่มี orders</p>
                            </div>
                        ) : (
                            couriers.map((courier) => (
                                <button
                                    key={courier.courier_code}
                                    className="mobile-card"
                                    onClick={() => handleSelectCourier(courier.courier_code)}
                                    style={{
                                        width: '100%',
                                        marginBottom: 12,
                                        padding: 16,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        cursor: 'pointer',
                                        border: 'none',
                                        textAlign: 'left'
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{
                                            width: 48,
                                            height: 48,
                                            borderRadius: 12,
                                            background: courier.courier_code?.includes('J&T') ? '#ef4444' :
                                                courier.courier_code?.includes('Flash') ? '#fbbf24' : '#6b7280',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: 'white',
                                            fontWeight: 700,
                                            fontSize: '0.8rem'
                                        }}>
                                            {courier.courier_code?.includes('J&T') ? 'J&T' :
                                                courier.courier_code?.includes('Flash') ? 'FL' : '📦'}
                                        </div>
                                        <div>
                                            <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                                                {courier.courier_name || courier.courier_code}
                                            </div>
                                            <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>
                                                แบ่ง {Math.ceil(courier.count / 100)} ไฟล์ (100 ใบ/ไฟล์)
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{
                                        fontSize: '1.5rem',
                                        fontWeight: 700,
                                        color: '#6366f1'
                                    }}>
                                        {courier.count.toLocaleString()}
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </>
            ) : (
                /* Download Files */
                <>
                    <div style={{ padding: '0 16px', marginBottom: 16 }}>
                        <div className="mobile-card" style={{
                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            color: 'white',
                            padding: 20
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{selectedCourier}</div>
                                    <div style={{ opacity: 0.9, marginTop: 4 }}>
                                        {batchInfo?.total_orders.toLocaleString()} orders → {batchInfo?.total_files} ไฟล์
                                    </div>
                                </div>
                                <button
                                    className="btn btn-light"
                                    onClick={handleDownloadAll}
                                    style={{ fontWeight: 600 }}
                                >
                                    <i className="bi bi-download me-2"></i>
                                    ดาวน์โหลดทั้งหมด
                                </button>
                            </div>
                        </div>
                    </div>

                    <div style={{ padding: '0 16px' }}>
                        <h5 style={{ marginBottom: 12, fontWeight: 600 }}>
                            <i className="bi bi-file-earmark-pdf me-2" style={{ color: '#ef4444' }}></i>
                            ไฟล์ PDF (เรียงตาม SKU)
                        </h5>

                        {batchInfo?.files.map((file, index) => (
                            <button
                                key={file.page}
                                className="mobile-card"
                                onClick={() => handleDownloadFile(file, index)}
                                disabled={downloading === index}
                                style={{
                                    width: '100%',
                                    marginBottom: 10,
                                    padding: 16,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    cursor: 'pointer',
                                    border: 'none',
                                    textAlign: 'left',
                                    opacity: downloading === index ? 0.7 : 1
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <div style={{
                                        width: 40,
                                        height: 40,
                                        borderRadius: 8,
                                        background: '#fee2e2',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#ef4444',
                                        fontWeight: 700
                                    }}>
                                        <i className="bi bi-file-pdf-fill"></i>
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 600 }}>
                                            ไฟล์ {file.page} / {batchInfo.total_files}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', opacity: 0.6 }}>
                                            {file.orders} ใบ
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    {downloading === index ? (
                                        <div className="spinner-border spinner-border-sm text-primary"></div>
                                    ) : (
                                        <i className="bi bi-download" style={{ fontSize: '1.2rem', color: '#6366f1' }}></i>
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* Back Button */}
                    <div style={{ padding: 16 }}>
                        <button
                            className="btn btn-outline-secondary w-100"
                            onClick={() => { setSelectedCourier(null); setBatchInfo(null); }}
                            style={{ padding: '12px 24px' }}
                        >
                            <i className="bi bi-arrow-left me-2"></i>
                            เลือกขนส่งอื่น
                        </button>
                    </div>
                </>
            )}
        </div>
    );
};

export default MobilePrintLabels;
