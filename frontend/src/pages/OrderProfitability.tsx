import React, { useState, useCallback, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface OrderProfit {
    order_number: string;
    platform: string;
    date: string;
    items: string;
    revenue: number;
    cogs: number;
    fees: number;
    net_profit: number;
    margin_percent: number;
}

const OrderProfitability: React.FC = () => {
    const [orders, setOrders] = useState<OrderProfit[]>([]);
    const [loading, setLoading] = useState(false);
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 7);
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => {
        return new Date().toISOString().split('T')[0];
    });
    const [platform, setPlatform] = useState('all');
    const [profitFilter, setProfitFilter] = useState('all');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get(`/finance/profitability?start_date=${startDate}T00:00:00&end_date=${endDate}T23:59:59`);
            setOrders(res.data || []);
        } catch (error) {
            console.error("Error fetching profitability:", error);
            setOrders([]);
        } finally {
            setLoading(false);
        }
    }, [startDate, endDate]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const formatNumber = (num: number) => {
        return num.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const getPlatformBadge = (p: string) => {
        const badges: Record<string, string> = {
            'shopee': 'bg-warning text-dark',
            'tiktok': 'bg-dark',
            'lazada': 'bg-primary',
            'line_shopping': 'bg-success',
            'manual': 'bg-secondary'
        };
        return badges[p?.toLowerCase()] || 'bg-secondary';
    };

    // Filter orders
    const filteredOrders = orders.filter(o => {
        if (platform !== 'all' && o.platform?.toLowerCase() !== platform) return false;
        if (profitFilter === 'profit' && o.net_profit <= 0) return false;
        if (profitFilter === 'loss' && o.net_profit >= 0) return false;
        return true;
    });

    // Summary calculations
    const summary = {
        totalOrders: filteredOrders.length,
        totalRevenue: filteredOrders.reduce((sum, o) => sum + o.revenue, 0),
        totalCogs: filteredOrders.reduce((sum, o) => sum + o.cogs, 0),
        totalFees: filteredOrders.reduce((sum, o) => sum + o.fees, 0),
        totalProfit: filteredOrders.reduce((sum, o) => sum + o.net_profit, 0),
        profitOrders: filteredOrders.filter(o => o.net_profit > 0).length,
        lossOrders: filteredOrders.filter(o => o.net_profit < 0).length
    };

    const breadcrumb = (
        <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
                <li className="breadcrumb-item"><a href="/finance">การเงิน</a></li>
                <li className="breadcrumb-item active">วิเคราะห์กำไร/Order</li>
            </ol>
        </nav>
    );

    return (
        <Layout
            title="📊 วิเคราะห์กำไร/Order"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2 align-items-center flex-wrap">
                    <input type="date" className="form-control form-control-sm" style={{ width: '130px' }}
                        value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                    <span className="text-muted">ถึง</span>
                    <input type="date" className="form-control form-control-sm" style={{ width: '130px' }}
                        value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                    <button className="btn btn-sm btn-primary" onClick={fetchData}>
                        <i className="bi bi-arrow-clockwise me-1"></i>โหลด
                    </button>
                </div>
            }
        >
            {/* Filters & Summary */}
            <div className="row g-3 mb-4">
                <div className="col-md-3">
                    <select className="form-select" value={platform} onChange={(e) => setPlatform(e.target.value)}>
                        <option value="all">ทุก Platform</option>
                        <option value="shopee">Shopee</option>
                        <option value="tiktok">TikTok</option>
                        <option value="lazada">Lazada</option>
                        <option value="manual">Manual</option>
                    </select>
                </div>
                <div className="col-md-3">
                    <select className="form-select" value={profitFilter} onChange={(e) => setProfitFilter(e.target.value)}>
                        <option value="all">ทั้งหมด</option>
                        <option value="profit">เฉพาะกำไร</option>
                        <option value="loss">เฉพาะขาดทุน</option>
                    </select>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="row g-3 mb-4">
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm bg-primary bg-opacity-10">
                        <div className="card-body text-center py-3">
                            <h6 className="text-muted mb-1">Orders</h6>
                            <h4 className="fw-bold mb-0 text-primary">{summary.totalOrders}</h4>
                        </div>
                    </div>
                </div>
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm bg-success bg-opacity-10">
                        <div className="card-body text-center py-3">
                            <h6 className="text-muted mb-1">รายได้</h6>
                            <h5 className="fw-bold mb-0 text-success">{formatNumber(summary.totalRevenue)}</h5>
                        </div>
                    </div>
                </div>
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm bg-warning bg-opacity-10">
                        <div className="card-body text-center py-3">
                            <h6 className="text-muted mb-1">ต้นทุน</h6>
                            <h5 className="fw-bold mb-0 text-warning">{formatNumber(summary.totalCogs)}</h5>
                        </div>
                    </div>
                </div>
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm bg-danger bg-opacity-10">
                        <div className="card-body text-center py-3">
                            <h6 className="text-muted mb-1">ค่าธรรมเนียม</h6>
                            <h5 className="fw-bold mb-0 text-danger">{formatNumber(summary.totalFees)}</h5>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className={`card border-0 shadow-sm ${summary.totalProfit >= 0 ? 'bg-success' : 'bg-danger'} bg-opacity-10`}>
                        <div className="card-body text-center py-3">
                            <h6 className="text-muted mb-1">กำไรสุทธิ</h6>
                            <h4 className={`fw-bold mb-0 ${summary.totalProfit >= 0 ? 'text-success' : 'text-danger'}`}>
                                {formatNumber(summary.totalProfit)} ฿
                            </h4>
                            <small className="text-muted">
                                กำไร {summary.profitOrders} | ขาดทุน {summary.lossOrders}
                            </small>
                        </div>
                    </div>
                </div>
            </div>

            {/* Orders Table */}
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    {loading ? (
                        <div className="text-center py-5">
                            <div className="spinner-border text-primary"></div>
                            <p className="mt-2 text-muted">กำลังโหลด...</p>
                        </div>
                    ) : filteredOrders.length === 0 ? (
                        <div className="text-center py-5 text-muted">
                            <i className="bi bi-inbox display-4"></i>
                            <p className="mt-2">ไม่พบข้อมูล</p>
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-hover mb-0 align-middle">
                                <thead className="bg-light">
                                    <tr>
                                        <th className="ps-4">วันที่</th>
                                        <th>Order</th>
                                        <th>Platform</th>
                                        <th>สินค้า</th>
                                        <th className="text-end">รายได้</th>
                                        <th className="text-end">ต้นทุน</th>
                                        <th className="text-end">ค่าธรรมเนียม</th>
                                        <th className="text-end">กำไร</th>
                                        <th className="text-end pe-4">Margin</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredOrders.slice(0, 100).map((o, idx) => (
                                        <tr key={idx}>
                                            <td className="ps-4 text-muted">{o.date}</td>
                                            <td>
                                                <code className="small">{o.order_number?.substring(0, 15)}...</code>
                                            </td>
                                            <td>
                                                <span className={`badge ${getPlatformBadge(o.platform)}`}>
                                                    {o.platform}
                                                </span>
                                            </td>
                                            <td>
                                                <small className="text-muted">{o.items?.substring(0, 30)}...</small>
                                            </td>
                                            <td className="text-end text-success">{formatNumber(o.revenue)}</td>
                                            <td className="text-end text-warning">{formatNumber(o.cogs)}</td>
                                            <td className="text-end text-danger">{formatNumber(o.fees)}</td>
                                            <td className={`text-end fw-bold ${o.net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                                {formatNumber(o.net_profit)}
                                            </td>
                                            <td className={`text-end pe-4 ${o.margin_percent >= 0 ? 'text-success' : 'text-danger'}`}>
                                                {o.margin_percent.toFixed(1)}%
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default OrderProfitability;
