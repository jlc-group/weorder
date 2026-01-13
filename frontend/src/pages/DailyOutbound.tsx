import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface OutboundItem {
    sku: string;
    product_name: string;
    total_quantity: number;
    order_count: number;
}

interface ReportData {
    date: string;
    total_items: number;
    total_orders: number;
    items: OutboundItem[];
    platforms?: Record<string, { orders: number, items: number }>;
}

const DailyOutbound: React.FC = () => {
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [reportData, setReportData] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(false);

    const loadReport = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await api.get(`/report/daily-outbound`, {
                params: { date: selectedDate }
            });
            setReportData(data);
        } catch (e) {
            console.error('Failed to load report:', e);
            alert('ไม่สามารถโหลดรายงานได้');
        } finally {
            setLoading(false);
        }
    }, [selectedDate]);

    useEffect(() => {
        loadReport();
    }, [loadReport]);

    const handleExport = () => {
        if (!reportData) return;

        // Simple CSV Export
        const headers = ['SKU', 'Product Name', 'Quantity', 'Orders Count'];
        const rows = reportData.items.map(item => [
            item.sku,
            `"${item.product_name.replace(/"/g, '""')}"`, // Escape quotes
            item.total_quantity,
            item.order_count
        ]);

        const csvContent = "data:text/csv;charset=utf-8,"
            + headers.join(",") + "\n"
            + rows.map(e => e.join(",")).join("\n");

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `daily_outbound_${selectedDate}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item">รายงาน</li>
            <li className="breadcrumb-item active">สรุปการส่งสินค้าประจำวัน</li>
        </>
    );

    // Helper for platform stats
    const getPlatformStat = (p: string) => {
        if (!reportData?.platforms) return { orders: 0, items: 0 };
        return reportData.platforms[p] || { orders: 0, items: 0 };
    };

    return (
        <Layout title="สรุปการส่งสินค้าประจำวัน (Daily Outbound)" breadcrumb={breadcrumb}>
            <div className="card border-0 shadow-sm mb-4">
                {/* ... (date picker card body) ... */}
                <div className="card-body">
                    <div className="row g-3 align-items-end">
                        <div className="col-md-3">
                            <label className="form-label">เลือกวันที่</label>
                            <input
                                type="date"
                                className="form-control"
                                value={selectedDate}
                                onChange={(e) => setSelectedDate(e.target.value)}
                            />
                        </div>
                        <div className="col-md-3">
                            <button
                                className="btn btn-primary w-100"
                                onClick={loadReport}
                                disabled={loading}
                            >
                                <i className={`bi ${loading ? 'bi-arrow-repeat spin' : 'bi-search'} me-2`}></i>
                                โหลดข้อมูล
                            </button>
                        </div>
                        <div className="col-md-6 text-end">
                            <button
                                className="btn btn-success"
                                onClick={handleExport}
                                disabled={!reportData || reportData.items.length === 0}
                            >
                                <i className="bi bi-file-earmark-excel me-2"></i> Export CSV
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {reportData && (
                <>
                    {/* Platform Breakdown */}
                    <div className="row g-3 mb-4">
                        <div className="col-md-4">
                            <div className="card text-dark h-100" style={{ backgroundColor: '#EE4D2D', color: 'white' }}> {/* Shopee Orange */}
                                <div className="card-body text-center text-white">
                                    <h6 className="card-title opacity-75">Shopee</h6>
                                    <h3 className="fw-bold mb-0">{getPlatformStat('shopee').items.toLocaleString()} ชิ้น</h3>
                                    <div className="small opacity-75">{getPlatformStat('shopee').orders.toLocaleString()} ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="card bg-dark text-white h-100"> {/* TikTok Black */}
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">TikTok Shop</h6>
                                    <h3 className="fw-bold mb-0">{getPlatformStat('tiktok').items.toLocaleString()} ชิ้น</h3>
                                    <div className="small opacity-75">{getPlatformStat('tiktok').orders.toLocaleString()} ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="card text-white h-100" style={{ backgroundColor: '#0f146d' }}> {/* Lazada Navy */}
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">Lazada</h6>
                                    <h3 className="fw-bold mb-0">{getPlatformStat('lazada').items.toLocaleString()} ชิ้น</h3>
                                    <div className="small opacity-75">{getPlatformStat('lazada').orders.toLocaleString()} ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Summary Cards (Total) */}
                    <div className="row g-3 mb-4">
                        <div className="col-md-6">
                            <div className="card bg-primary text-white h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">จำนวนสินค้าทั้งหมด (ชิ้น)</h6>
                                    <h2 className="display-4 fw-bold">{reportData.total_items.toLocaleString()}</h2>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-6">
                            <div className="card bg-info text-dark h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">จำนวนออเดอร์ที่จัดส่ง</h6>
                                    <h2 className="display-4 fw-bold">{reportData.total_orders.toLocaleString()}</h2>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Table */}
                    <div className="card border-0 shadow-sm">
                        <div className="card-header bg-white py-3">
                            <h5 className="card-title mb-0">รายการสินค้าที่จัดส่งสำเร็จ/กำลังจัดส่ง</h5>
                        </div>
                        <div className="table-responsive">
                            <table className="table table-hover align-middle mb-0">
                                <thead className="table-light">
                                    <tr>
                                        <th>SKU</th>
                                        <th>ชื่อสินค้า</th>
                                        <th className="text-center">จำนวนที่ส่ง (ชิ้น)</th>
                                        <th className="text-center">จำนวนออเดอร์</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {reportData.items.length === 0 ? (
                                        <tr>
                                            <td colSpan={4} className="text-center py-5 text-muted">
                                                ไม่พบข้อมูลการจัดส่งในวันนี้
                                            </td>
                                        </tr>
                                    ) : (
                                        reportData.items.map((item, idx) => (
                                            <tr key={idx}>
                                                <td className="fw-mono fw-semibold text-primary">{item.sku}</td>
                                                <td>{item.product_name}</td>
                                                <td className="text-center fw-bold fs-5">{(item.total_quantity || 0).toLocaleString()}</td>
                                                <td className="text-center text-muted">{item.order_count.toLocaleString()}</td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </Layout>
    );
};

export default DailyOutbound;
