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
    preview?: { sku: string; name: string; qty: number; orders: number }[];
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
    const [printMode, setPrintMode] = useState<'batch' | 'sku'>('batch');
    const [skuGroups, setSkuGroups] = useState<any[]>([]);

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

    // Load SKU groups when mode is sku
    useEffect(() => {
        if (selectedCourier && printMode === 'sku') {
            loadSkuGroups();
        }
    }, [selectedCourier, printMode, status, selectedPlatform]);

    const loadPlatformSummary = async () => {
        try {
            const { data } = await api.get(`/labels/platform-summary?status=${status}`);
            setPlatforms(data.platforms || []);
        } catch (e) {
            console.error('Failed to load platform summary:', e);
        }
    };

    const loadSkuGroups = async () => {
        setLoading(true);
        try {
            let url = `/labels/sku-summary?courier=${selectedCourier}&status=${status}`;
            if (selectedPlatform) {
                url += `&channel=${selectedPlatform}`;
            }
            const { data } = await api.get(url);
            setSkuGroups(data.groups || []);
        } catch (e) {
            console.error('Failed to load SKU groups:', e);
        } finally {
            setLoading(false);
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
        setPrintMode('batch'); // Default to batch mode
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

            {/* Mode Selection & Results */}
            {selectedCourier && (
                <div className="card shadow-sm">
                    <div className="card-header bg-white p-0">
                        <ul className="nav nav-tabs card-header-tabs m-0 px-3 pt-3">
                            <li className="nav-item">
                                <a
                                    className={`nav-link py-3 fw-bold ${printMode === 'batch' ? 'active text-primary' : 'text-muted'}`}
                                    onClick={() => setPrintMode('batch')}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <i className="bi bi-files me-2"></i>
                                    แยกตามไฟล์ (Batch)
                                </a>
                            </li>
                            <li className="nav-item">
                                <a
                                    className={`nav-link py-3 fw-bold ${printMode === 'sku' ? 'active text-primary' : 'text-muted'}`}
                                    onClick={() => setPrintMode('sku')}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <i className="bi bi-box-seam me-2"></i>
                                    แยกตามสินค้า (SKU Group)
                                </a>
                            </li>
                        </ul>
                    </div>

                    <div className="card-body bg-light">
                        {printMode === 'batch' ? (
                            batchFiles.length > 0 ? (
                                <div>
                                    <div className="d-flex justify-content-between align-items-center mb-4">
                                        <h5 className="mb-0 text-success">
                                            <i className="bi bi-check-circle-fill me-2"></i>
                                            พร้อมดาวน์โหลด {batchFiles.length} ไฟล์ ({totalOrders} orders)
                                        </h5>
                                        <button
                                            className="btn btn-success btn-lg shadow-sm"
                                            onClick={handleDownloadAll}
                                        >
                                            <i className="bi bi-cloud-download me-2"></i>
                                            Download All
                                        </button>
                                    </div>
                                    <div className="row g-3">
                                        {batchFiles.map((file, index) => (
                                            <div key={file.page} className="col-md-6 col-lg-4">
                                                <div className={`card h-100 shadow-sm ${downloadingIndex === index ? 'border-success' : ''}`}>
                                                    <div className="card-header bg-white d-flex justify-content-between align-items-center py-2">
                                                        <div>
                                                            <i className="bi bi-file-earmark-pdf text-danger me-2"></i>
                                                            <strong>ไฟล์ {file.page}</strong>
                                                            <span className="badge bg-secondary ms-2">{file.orders} ใบ</span>
                                                        </div>
                                                        <button
                                                            className={`btn btn-sm ${downloadingIndex === index ? 'btn-success' : 'btn-outline-success'}`}
                                                            onClick={() => handleDownloadFile(file, index)}
                                                            disabled={downloadingIndex === index}
                                                        >
                                                            {downloadingIndex === index ? (
                                                                <span className="spinner-border spinner-border-sm"></span>
                                                            ) : (
                                                                <><i className="bi bi-download me-1"></i>Download</>
                                                            )}
                                                        </button>
                                                    </div>
                                                    <div className="card-body py-2">
                                                        {file.preview && file.preview.length > 0 ? (
                                                            <div className="small">
                                                                <div className="text-muted mb-1">สินค้าหลัก:</div>
                                                                {file.preview.slice(0, 3).map((p, i) => (
                                                                    <div key={i} className="d-flex justify-content-between align-items-center py-1 border-bottom">
                                                                        <span className="text-truncate" style={{ maxWidth: '180px' }} title={p.name}>
                                                                            <span className="text-primary fw-bold">{p.sku}</span>
                                                                            <span className="text-muted ms-1 small">{p.name?.substring(0, 20)}</span>
                                                                        </span>
                                                                        <span className="badge bg-dark">{p.qty} ชิ้น</span>
                                                                    </div>
                                                                ))}
                                                                {file.preview.length > 3 && (
                                                                    <div className="text-muted small mt-1">+{file.preview.length - 3} รายการอื่น</div>
                                                                )}
                                                            </div>
                                                        ) : (
                                                            <div className="text-muted small">ไม่มีข้อมูลสินค้า</div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-5">
                                    <i className="bi bi-inbox fs-1 text-muted d-block mb-3"></i>
                                    <p className="text-muted">ไม่พบออเดอร์ในเงื่อนไขนี้</p>
                                </div>
                            )
                        ) : (
                            /* SKU MODE */
                            <div className="table-responsive bg-white rounded shadow-sm">
                                <table className="table table-hover align-middle mb-0">
                                    <thead className="bg-light text-muted">
                                        <tr>
                                            <th className="py-3 ps-4">รายการสินค้า (SKU Group)</th>
                                            <th className="py-3 text-center" style={{ width: '150px' }}>จำนวนออเดอร์</th>
                                            <th className="py-3 text-end pe-4" style={{ width: '200px' }}>ดาวน์โหลด</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {skuGroups.length === 0 ? (
                                            <tr>
                                                <td colSpan={3} className="text-center py-5 text-muted">
                                                    กำลังโหลดข้อมูลสินค้า...
                                                </td>
                                            </tr>
                                        ) : (
                                            skuGroups.map((group, idx) => (
                                                <tr key={idx}>
                                                    <td className="ps-4">
                                                        <div className="d-flex flex-column gap-2 py-2">
                                                            {group.items.map((item: any, i: number) => (
                                                                <div key={i} className="d-flex align-items-center">
                                                                    <span className="badge bg-secondary me-2">{item.qty} ชิ้น</span>
                                                                    <span className="fw-bold me-2 text-primary">{item.sku}</span>
                                                                    <span className="text-muted small text-truncate" style={{ maxWidth: '300px' }}>{item.name}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </td>
                                                    <td className="text-center">
                                                        <span className="badge bg-dark fs-6 pill px-3 py-2">{group.count}</span>
                                                    </td>
                                                    <td className="text-end pe-4">
                                                        <button
                                                            className="btn btn-outline-primary btn-sm"
                                                            onClick={() => {
                                                                const ids = group.order_ids.join(',');
                                                                window.open(`http://localhost:9203/api/orders/batch-labels?ids=${ids}&format=pdf`, '_blank');
                                                            }}
                                                        >
                                                            <i className="bi bi-printer me-2"></i>
                                                            พิมพ์ ({group.count})
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default PrintLabelsPage;
