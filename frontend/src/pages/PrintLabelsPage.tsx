import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface PlatformSummary {
    channel: string;
    channel_name: string;
    count: number;
}

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

const PrintLabelsPage: React.FC = () => {
    const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
    const [selectedPlatform, setSelectedPlatform] = useState<string>('');
    const [status, setStatus] = useState<string>('READY_TO_SHIP');
    const [couriers, setCouriers] = useState<CourierSummary[]>([]);
    const [selectedCourier, setSelectedCourier] = useState<string>('');
    const [batchFiles, setBatchFiles] = useState<BatchFile[]>([]);
    const [totalOrders, setTotalOrders] = useState(0);
    const [loading, setLoading] = useState(false);
    const [downloadingIndex, setDownloadingIndex] = useState<number | null>(null);
    const [batchSize, setBatchSize] = useState<number>(50);

    // Load platform summary
    useEffect(() => {
        loadPlatformSummary();
    }, [status]);

    // Load courier summary when platform changes
    useEffect(() => {
        if (selectedPlatform || selectedPlatform === '') {
            loadCourierSummary();
        }
    }, [selectedPlatform, status]);

    const loadPlatformSummary = async () => {
        try {
            const { data } = await api.get(`/labels/platform-summary?status=${status}`);
            setPlatforms(data.platforms || []);
        } catch (e) {
            console.error('Failed to load platform summary:', e);
        }
    };

    const loadCourierSummary = async () => {
        setLoading(true);
        try {
            let url = `/labels/courier-summary?status=${status}`;
            if (selectedPlatform) {
                url += `&channel=${selectedPlatform}`;
            }
            const { data } = await api.get(url);
            setCouriers(data.couriers || []);
            setTotalOrders(data.total || 0);
        } catch (e) {
            console.error('Failed to load courier summary:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleSelectCourier = async (courierCode: string) => {
        setSelectedCourier(courierCode);
        setLoading(true);
        try {
            const { data } = await api.post('/labels/print-batch', {
                courier: courierCode,
                status: status,
                channel: selectedPlatform || null,
                max_per_file: batchSize,
                sort_by_sku: true
            });

            setBatchFiles(data.files || []);
            setTotalOrders(data.total_orders || 0);
        } catch (e) {
            console.error('Failed to load batch:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadFile = async (file: BatchFile, index: number) => {
        setDownloadingIndex(index);
        try {
            // Build URL with optional channel
            let url = `/labels/by-courier?courier=${encodeURIComponent(selectedCourier)}&status=${status}&page=${file.page}&per_page=${batchSize}&sort_by_sku=true`;
            if (selectedPlatform) {
                url += `&channel=${selectedPlatform}`;
            }
            window.open(`http://localhost:9203/api${url}`, '_blank');
        } catch (e) {
            console.error('Download failed:', e);
        } finally {
            setTimeout(() => setDownloadingIndex(null), 1000);
        }
    };

    const handleDownloadAll = async () => {
        for (let i = 0; i < batchFiles.length; i++) {
            await handleDownloadFile(batchFiles[i], i);
            // Delay between downloads
            await new Promise(r => setTimeout(r, 500));
        }
    };

    const getPlatformIcon = (channel: string) => {
        const icons: Record<string, string> = {
            'tiktok': 'bi-tiktok',
            'shopee': 'bi-cart-fill',
            'lazada': 'bi-bag-fill'
        };
        return icons[channel.toLowerCase()] || 'bi-shop';
    };

    const getPlatformColor = (channel: string) => {
        const colors: Record<string, string> = {
            'tiktok': '#000000',
            'shopee': '#ee4d2d',
            'lazada': '#0f146d'
        };
        return colors[channel.toLowerCase()] || '#6c757d';
    };

    return (
        <Layout
            title="พิมพ์ใบปะหน้า"
            breadcrumb={
                <>
                    <li className="breadcrumb-item">Packing</li>
                    <li className="breadcrumb-item active">Print Labels</li>
                </>
            }
        >
            {/* Status & Batch Size Selection */}
            <div className="card mb-4">
                <div className="card-body">
                    <div className="row g-3 align-items-end">
                        <div className="col-md-3">
                            <label className="form-label fw-bold">สถานะ Order</label>
                            <select
                                className="form-select form-select-lg"
                                value={status}
                                onChange={(e) => setStatus(e.target.value)}
                            >
                                <option value="READY_TO_SHIP">รอจัดส่ง (Ready to Ship)</option>
                                <option value="PAID">รอแพ็ค (Paid)</option>
                            </select>
                        </div>
                        <div className="col-md-3">
                            <label className="form-label fw-bold">จำนวนต่อไฟล์</label>
                            <select
                                className="form-select form-select-lg"
                                value={batchSize}
                                onChange={(e) => setBatchSize(Number(e.target.value))}
                            >
                                <option value={25}>25 ใบ/ไฟล์</option>
                                <option value={50}>50 ใบ/ไฟล์ (แนะนำ)</option>
                                <option value={100}>100 ใบ/ไฟล์</option>
                            </select>
                        </div>
                        <div className="col-md-6 text-end">
                            <div className="fs-5 text-muted">
                                รวมทั้งหมด: <strong className="text-dark fs-3">{totalOrders.toLocaleString()}</strong> orders
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Platform Selection */}
            <div className="card mb-4">
                <div className="card-header bg-light">
                    <h5 className="mb-0">
                        <i className="bi bi-grid-fill me-2"></i>
                        เลือก Platform
                    </h5>
                </div>
                <div className="card-body">
                    <div className="row g-3">
                        {/* All Platforms Option */}
                        <div className="col-md-3">
                            <div
                                className={`card h-100 cursor-pointer border-3 ${selectedPlatform === '' ? 'border-primary shadow' : 'border-light'}`}
                                onClick={() => setSelectedPlatform('')}
                                style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                            >
                                <div className="card-body text-center py-4">
                                    <i className="bi bi-collection-fill fs-1 text-primary mb-2 d-block"></i>
                                    <h5 className="mb-1">ทั้งหมด</h5>
                                    <div className="badge bg-primary fs-6">
                                        {platforms.reduce((sum, p) => sum + p.count, 0).toLocaleString()}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Platform Cards */}
                        {platforms.map(platform => (
                            <div key={platform.channel} className="col-md-3">
                                <div
                                    className={`card h-100 cursor-pointer border-3 ${selectedPlatform === platform.channel ? 'border-primary shadow' : 'border-light'}`}
                                    onClick={() => setSelectedPlatform(platform.channel)}
                                    style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                                >
                                    <div className="card-body text-center py-4">
                                        <i
                                            className={`${getPlatformIcon(platform.channel)} fs-1 mb-2 d-block`}
                                            style={{ color: getPlatformColor(platform.channel) }}
                                        ></i>
                                        <h5 className="mb-1">{platform.channel_name}</h5>
                                        <div
                                            className="badge fs-6"
                                            style={{ backgroundColor: getPlatformColor(platform.channel) }}
                                        >
                                            {platform.count.toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Courier Selection */}
            <div className="card mb-4">
                <div className="card-header bg-light">
                    <h5 className="mb-0">
                        <i className="bi bi-truck me-2"></i>
                        เลือกขนส่ง {selectedPlatform ? `(${selectedPlatform})` : '(ทั้งหมด)'}
                    </h5>
                </div>
                <div className="card-body">
                    {loading ? (
                        <div className="text-center py-5">
                            <div className="spinner-border text-primary" role="status"></div>
                            <p className="mt-2 text-muted">กำลังโหลด...</p>
                        </div>
                    ) : couriers.length === 0 ? (
                        <div className="text-center py-5 text-muted">
                            <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                            ไม่พบ orders ในสถานะนี้
                        </div>
                    ) : (
                        <div className="row g-3">
                            {couriers.map(courier => (
                                <div key={courier.courier_code} className="col-md-4">
                                    <div
                                        className={`card h-100 border-2 ${selectedCourier === courier.courier_code ? 'border-success bg-success bg-opacity-10' : 'border-light'}`}
                                        onClick={() => handleSelectCourier(courier.courier_code)}
                                        style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                                    >
                                        <div className="card-body d-flex justify-content-between align-items-center">
                                            <div>
                                                <h6 className="mb-0 fw-bold">{courier.courier_name}</h6>
                                                <small className="text-muted text-truncate d-block" style={{ maxWidth: '200px' }}>
                                                    {courier.courier_code}
                                                </small>
                                            </div>
                                            <div className="text-end">
                                                <span className="badge bg-dark fs-5">{courier.count.toLocaleString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Download Section */}
            {selectedCourier && batchFiles.length > 0 && (
                <div className="card border-success">
                    <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
                        <h5 className="mb-0">
                            <i className="bi bi-download me-2"></i>
                            ดาวน์โหลด PDF ({batchFiles.length} ไฟล์, {totalOrders} orders)
                        </h5>
                        <button
                            className="btn btn-light btn-lg"
                            onClick={handleDownloadAll}
                        >
                            <i className="bi bi-cloud-download me-2"></i>
                            Download All
                        </button>
                    </div>
                    <div className="card-body">
                        <div className="row g-3">
                            {batchFiles.map((file, index) => (
                                <div key={file.page} className="col-md-3">
                                    <button
                                        className={`btn w-100 py-3 ${downloadingIndex === index ? 'btn-success' : 'btn-outline-success'}`}
                                        onClick={() => handleDownloadFile(file, index)}
                                        disabled={downloadingIndex === index}
                                    >
                                        {downloadingIndex === index ? (
                                            <>
                                                <span className="spinner-border spinner-border-sm me-2"></span>
                                                กำลังดาวน์โหลด...
                                            </>
                                        ) : (
                                            <>
                                                <i className="bi bi-file-pdf fs-4 d-block mb-1"></i>
                                                <strong>ไฟล์ {file.page}</strong>
                                                <br />
                                                <small>{file.orders} ใบ</small>
                                            </>
                                        )}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default PrintLabelsPage;
