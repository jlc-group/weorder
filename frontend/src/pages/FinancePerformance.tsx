import React, { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface InternalExpense {
    title: string;
    amount: number;
    category: string;
    date: string;
}

interface PlatformPerformance {
    platform: string;
    product_sales: number;
    shipping_income: number;
    tax_revenue: number;
    platform_fees: number;
    shipping_cost: number;
    cash_fees: number;
    cash_payout: number;
    cogs_ex_vat: number;
    cogs_inc_vat: number;
    net_profit_tax: number;
}

interface PerformanceData {
    period: { start: string; end: string; };
    summary: {
        total_product_sales: number;
        total_shipping_income: number;
        total_tax_revenue: number;
        total_cogs_ex_vat: number;
        total_cogs_inc_vat: number;
        total_platform_fees: number;
        total_shipping_cost: number;
        total_fees: number;
        gross_profit: number;
        total_internal_expense: number;
        true_net_profit: number;
    };
    internal_expenses: InternalExpense[];
    platforms: PlatformPerformance[];
}

const FinancePerformance: React.FC = () => {
    const [data, setData] = useState<PerformanceData | null>(null);
    const [loading, setLoading] = useState(true);
    const [showFeeDetails, setShowFeeDetails] = useState(false);
    const [feeDetails, setFeeDetails] = useState<any>(null);
    const [feeLoading, setFeeLoading] = useState(false);
    const [startDate, setStartDate] = useState(
        new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]
    );
    const [endDate, setEndDate] = useState(
        new Date().toISOString().split('T')[0]
    );

    const fetchFeeDetails = async () => {
        setFeeLoading(true);
        try {
            const res = await api.get(`/finance/fee-details?start_date=${startDate}&end_date=${endDate}`);
            setFeeDetails(res.data);
        } catch (error) {
            console.error("Error fetching fee details:", error);
        } finally {
            setFeeLoading(false);
        }
    };

    const handleShowFeeDetails = () => {
        setShowFeeDetails(true);
        fetchFeeDetails();
    };

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get(`/finance/performance?start_date=${startDate}&end_date=${endDate}`);
            setData(res.data);
        } catch (error) {
            console.error("Error fetching finance performance:", error);
            setData(null);
        } finally {
            setLoading(false);
        }
    }, [startDate, endDate]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const formatMoney = (num: number) => {
        const abs = Math.abs(num);
        if (abs >= 1000000) {
            return (num / 1000000).toFixed(2) + ' ล้าน';
        }
        return num.toLocaleString('th-TH', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' ฿';
    };

    const formatNumber = (num: number) => {
        return num.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const getPlatformName = (platform: string) => {
        const names: Record<string, string> = {
            'shopee': '🟠 Shopee',
            'tiktok': '⚫ TikTok',
            'lazada': '🔵 Lazada',
            'line_shopping': '🟢 LINE Shopping',
            'manual': '📝 ขายตรง'
        };
        return names[platform] || platform;
    };

    const breadcrumb = (
        <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
                <li className="breadcrumb-item"><a href="/finance">การเงิน</a></li>
                <li className="breadcrumb-item active">สรุปผลประกอบการ</li>
            </ol>
        </nav>
    );

    return (
        <Layout
            title="📊 สรุปผลประกอบการ"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2 align-items-center flex-wrap">
                    <span className="text-muted small me-1">ช่วงเวลา:</span>
                    <input type="date" className="form-control form-control-sm" style={{ width: '140px' }}
                        value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                    <span className="text-muted">ถึง</span>
                    <input type="date" className="form-control form-control-sm" style={{ width: '140px' }}
                        value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                    <button className="btn btn-sm btn-primary" onClick={fetchData}>
                        <i className="bi bi-arrow-clockwise me-1"></i>โหลดใหม่
                    </button>
                    <button className="btn btn-sm btn-success" onClick={() => {
                        window.open(`${api.defaults.baseURL}/finance/export?start_date=${startDate}&end_date=${endDate}`, '_blank');
                    }}>
                        <i className="bi bi-download me-1"></i>ดาวน์โหลด
                    </button>
                </div>
            }
        >
            {loading ? (
                <div className="text-center py-5">
                    <div className="spinner-border text-primary"></div>
                    <p className="mt-2 text-muted">กำลังโหลดข้อมูล...</p>
                </div>
            ) : !data ? (
                <div className="alert alert-warning">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    ไม่พบข้อมูลในช่วงเวลาที่เลือก
                </div>
            ) : (
                <div className="row g-4">
                    {/* ===== Section 1: สรุปภาพรวม ===== */}
                    <div className="col-12">
                        <h5 className="mb-3"><i className="bi bi-pie-chart me-2"></i>สรุปภาพรวม</h5>
                        <div className="row g-3">
                            {/* กำไรสุทธิ */}
                            <div className="col-md-6 col-lg-3">
                                <div className={`card h-100 border-0 shadow-sm ${data.summary.true_net_profit >= 0 ? 'bg-success bg-opacity-10' : 'bg-danger bg-opacity-10'}`}>
                                    <div className="card-body text-center">
                                        <div className="display-6 mb-2">
                                            {data.summary.true_net_profit >= 0 ? '😊' : '😟'}
                                        </div>
                                        <h6 className="text-muted mb-1">กำไรสุทธิ</h6>
                                        <h3 className={`fw-bold mb-0 ${data.summary.true_net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                            {formatMoney(data.summary.true_net_profit)}
                                        </h3>
                                        <small className="text-muted">หลังหักทุกอย่างแล้ว</small>
                                    </div>
                                </div>
                            </div>
                            {/* ยอดขาย */}
                            <div className="col-md-6 col-lg-3">
                                <div className="card h-100 border-0 shadow-sm bg-primary bg-opacity-10">
                                    <div className="card-body text-center">
                                        <div className="display-6 mb-2">💰</div>
                                        <h6 className="text-muted mb-1">ยอดขายรวม</h6>
                                        <h3 className="fw-bold mb-0 text-primary">{formatMoney(data.summary.total_tax_revenue)}</h3>
                                        <small className="text-muted">รายได้ที่ต้องเสียภาษี</small>
                                    </div>
                                </div>
                            </div>
                            {/* ต้นทุนสินค้า */}
                            <div className="col-md-6 col-lg-3">
                                <div className="card h-100 border-0 shadow-sm bg-warning bg-opacity-10">
                                    <div className="card-body text-center">
                                        <div className="display-6 mb-2">📦</div>
                                        <h6 className="text-muted mb-1">ต้นทุนสินค้า</h6>
                                        <h3 className="fw-bold mb-0 text-warning">{formatMoney(data.summary.total_cogs_ex_vat)}</h3>
                                        <small className="text-muted">COGS (ไม่รวม VAT)</small>
                                    </div>
                                </div>
                            </div>
                            {/* ค่าธรรมเนียม */}
                            <div className="col-md-6 col-lg-3">
                                <div className="card h-100 border-0 shadow-sm bg-danger bg-opacity-10">
                                    <div className="card-body text-center">
                                        <div className="display-6 mb-2">🏷️</div>
                                        <h6 className="text-muted mb-1">ค่าธรรมเนียม Platform</h6>
                                        <h3 className="fw-bold mb-0 text-danger">{formatMoney(Math.abs(data.summary.total_fees))}</h3>
                                        <small className="text-muted">ค่า Commission + ค่าส่ง</small>
                                        <div className="mt-2">
                                            <button
                                                className="btn btn-sm btn-outline-danger"
                                                onClick={handleShowFeeDetails}
                                            >
                                                <i className="bi bi-list-ul me-1"></i>ดูรายละเอียด
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Fee Details Modal */}
                    {showFeeDetails && (
                        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                            <div className="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                                <div className="modal-content">
                                    <div className="modal-header bg-danger text-white">
                                        <h5 className="modal-title">
                                            <i className="bi bi-receipt me-2"></i>รายละเอียดค่าธรรมเนียม
                                        </h5>
                                        <button
                                            type="button"
                                            className="btn-close btn-close-white"
                                            onClick={() => setShowFeeDetails(false)}
                                        ></button>
                                    </div>
                                    <div className="modal-body">
                                        {feeLoading ? (
                                            <div className="text-center py-5">
                                                <div className="spinner-border text-primary"></div>
                                                <p className="mt-2 text-muted">กำลังโหลดข้อมูล...</p>
                                            </div>
                                        ) : feeDetails ? (
                                            <div className="row g-4">
                                                {Object.values(feeDetails.platforms || {}).map((platform: any) => (
                                                    <div key={platform.platform_name} className="col-md-6">
                                                        <div className="card h-100">
                                                            <div className="card-header bg-light">
                                                                <h6 className="mb-0 fw-bold">
                                                                    {platform.platform_name === 'TikTok Shop' && '⚫'}
                                                                    {platform.platform_name === 'Shopee' && '🟠'}
                                                                    {platform.platform_name === 'Lazada' && '🔵'}
                                                                    {' '}{platform.platform_name}
                                                                </h6>
                                                                {platform.order_count && (
                                                                    <small className="text-muted">{platform.order_count.toLocaleString()} ออเดอร์</small>
                                                                )}
                                                            </div>
                                                            <div className="card-body p-0">
                                                                <table className="table table-sm mb-0">
                                                                    <tbody>
                                                                        {platform.details?.filter((d: any) => d.amount !== 0).map((detail: any, idx: number) => (
                                                                            <tr key={idx}>
                                                                                <td className="ps-3">
                                                                                    <small>{detail.name}</small>
                                                                                </td>
                                                                                <td className="text-end pe-3 text-danger">
                                                                                    {formatNumber(detail.amount)}
                                                                                </td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                    <tfoot className="table-danger">
                                                                        <tr>
                                                                            <td className="ps-3 fw-bold">รวมค่าธรรมเนียม</td>
                                                                            <td className="text-end pe-3 fw-bold">
                                                                                {formatNumber(platform.total_fees || 0)}
                                                                            </td>
                                                                        </tr>
                                                                    </tfoot>
                                                                </table>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}

                                                {/* Total Summary */}
                                                <div className="col-12">
                                                    <div className="alert alert-danger mb-0">
                                                        <div className="d-flex justify-content-between align-items-center">
                                                            <span className="fw-bold fs-5">
                                                                <i className="bi bi-calculator me-2"></i>
                                                                ค่าธรรมเนียมทั้งหมด
                                                            </span>
                                                            <span className="fw-bold fs-4">
                                                                {formatNumber(feeDetails.total_fees || 0)} ฿
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="alert alert-warning mb-0">
                                                <i className="bi bi-exclamation-triangle me-2"></i>
                                                ไม่พบข้อมูลค่าธรรมเนียม
                                            </div>
                                        )}
                                    </div>
                                    <div className="modal-footer">
                                        <button
                                            type="button"
                                            className="btn btn-secondary"
                                            onClick={() => setShowFeeDetails(false)}
                                        >
                                            ปิด
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ===== Section 2: รายละเอียดการคำนวณ ===== */}
                    <div className="col-12">
                        <div className="card border-0 shadow-sm">
                            <div className="card-header bg-white py-3">
                                <h5 className="mb-0"><i className="bi bi-calculator me-2"></i>รายละเอียดการคำนวณกำไร</h5>
                            </div>
                            <div className="card-body">
                                <div className="row">
                                    <div className="col-md-6">
                                        <h6 className="text-success mb-3"><i className="bi bi-plus-circle me-2"></i>รายรับ (+)</h6>
                                        <table className="table table-sm">
                                            <tbody>
                                                <tr>
                                                    <td>ยอดขายสินค้า</td>
                                                    <td className="text-end fw-bold text-success">+{formatNumber(data.summary.total_product_sales)}</td>
                                                </tr>
                                                <tr>
                                                    <td>ค่าส่งที่เก็บจากลูกค้า</td>
                                                    <td className="text-end fw-bold text-success">+{formatNumber(data.summary.total_shipping_income)}</td>
                                                </tr>
                                                <tr className="table-success">
                                                    <td className="fw-bold">รวมรายรับ</td>
                                                    <td className="text-end fw-bold">+{formatNumber(data.summary.total_tax_revenue)}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <div className="col-md-6">
                                        <h6 className="text-danger mb-3"><i className="bi bi-dash-circle me-2"></i>รายจ่าย (-)</h6>
                                        <table className="table table-sm">
                                            <tbody>
                                                <tr>
                                                    <td>ต้นทุนสินค้า (COGS)</td>
                                                    <td className="text-end fw-bold text-danger">-{formatNumber(data.summary.total_cogs_ex_vat)}</td>
                                                </tr>
                                                <tr>
                                                    <td>ค่าธรรมเนียม Platform</td>
                                                    <td className="text-end fw-bold text-danger">{formatNumber(data.summary.total_platform_fees)}</td>
                                                </tr>
                                                <tr>
                                                    <td>ค่าส่งที่ Platform หัก</td>
                                                    <td className="text-end fw-bold text-danger">{formatNumber(data.summary.total_shipping_cost)}</td>
                                                </tr>
                                                <tr className="table-danger">
                                                    <td className="fw-bold">รวมรายจ่าย</td>
                                                    <td className="text-end fw-bold">{formatNumber(data.summary.total_fees - data.summary.total_cogs_ex_vat)}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                                <hr />
                                <div className="row">
                                    <div className="col-12 text-center">
                                        <h5 className="text-muted mb-2">กำไรสุทธิ = รายรับ - รายจ่าย</h5>
                                        <h2 className={`fw-bold ${data.summary.true_net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                            {formatNumber(data.summary.true_net_profit)} บาท
                                        </h2>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* ===== Section 3: แยกตาม Platform ===== */}
                    <div className="col-12">
                        <div className="card border-0 shadow-sm">
                            <div className="card-header bg-white py-3">
                                <h5 className="mb-0"><i className="bi bi-shop me-2"></i>แยกตาม Platform</h5>
                            </div>
                            <div className="card-body p-0">
                                <div className="table-responsive">
                                    <table className="table table-hover mb-0 align-middle">
                                        <thead className="bg-light">
                                            <tr>
                                                <th className="ps-4">Platform</th>
                                                <th className="text-end text-success">ยอดขาย</th>
                                                <th className="text-end text-danger">ค่าธรรมเนียม</th>
                                                <th className="text-end text-warning">ต้นทุน</th>
                                                <th className="text-end fw-bold">กำไร</th>
                                                <th className="text-end text-info">เงินเข้าบัญชี</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.platforms.filter(p => p.tax_revenue > 0 || p.cash_payout > 0).map(p => (
                                                <tr key={p.platform}>
                                                    <td className="ps-4 fw-bold">{getPlatformName(p.platform)}</td>
                                                    <td className="text-end text-success">{formatNumber(p.tax_revenue)}</td>
                                                    <td className="text-end text-danger">{formatNumber(p.cash_fees)}</td>
                                                    <td className="text-end text-warning">{formatNumber(p.cogs_ex_vat)}</td>
                                                    <td className={`text-end fw-bold ${p.net_profit_tax >= 0 ? 'text-success' : 'text-danger'}`}>
                                                        {formatNumber(p.net_profit_tax)}
                                                    </td>
                                                    <td className="text-end text-info fw-bold">{formatNumber(p.cash_payout)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot className="bg-light fw-bold">
                                            <tr>
                                                <td className="ps-4">รวมทั้งหมด</td>
                                                <td className="text-end text-success">{formatNumber(data.summary.total_tax_revenue)}</td>
                                                <td className="text-end text-danger">{formatNumber(data.summary.total_fees)}</td>
                                                <td className="text-end text-warning">{formatNumber(data.summary.total_cogs_ex_vat)}</td>
                                                <td className={`text-end ${data.summary.true_net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                                    {formatNumber(data.summary.true_net_profit)}
                                                </td>
                                                <td className="text-end text-info">
                                                    {formatNumber(data.platforms.reduce((acc, p) => acc + p.cash_payout, 0))}
                                                </td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* ===== Section 4: ค่าใช้จ่ายภายใน ===== */}
                    {data.internal_expenses.length > 0 && (
                        <div className="col-12">
                            <div className="card border-0 shadow-sm">
                                <div className="card-header bg-white py-3">
                                    <h5 className="mb-0"><i className="bi bi-receipt me-2"></i>ค่าใช้จ่ายบริษัท</h5>
                                </div>
                                <div className="card-body p-0">
                                    <table className="table table-hover mb-0">
                                        <thead className="bg-light">
                                            <tr>
                                                <th className="ps-4">วันที่</th>
                                                <th>รายการ</th>
                                                <th>หมวดหมู่</th>
                                                <th className="text-end pe-4">จำนวนเงิน</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.internal_expenses.map((e, idx) => (
                                                <tr key={idx}>
                                                    <td className="ps-4 text-muted">{new Date(e.date).toLocaleDateString('th-TH')}</td>
                                                    <td>{e.title}</td>
                                                    <td><span className="badge bg-secondary">{e.category}</span></td>
                                                    <td className="text-end pe-4 text-danger fw-bold">-{formatNumber(e.amount)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </Layout>
    );
};

export default FinancePerformance;
