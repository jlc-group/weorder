import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import { Link } from 'react-router-dom';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
);

interface SalesTrendItem {
    date: string;
    revenue: number;
}

interface TopProductItem {
    sku: string;
    product_name: string;
    total_qty: number;
    total_sales: number;
}

interface PlatformStats {
    platform: string;
    count: number;
    revenue: number;
    paid_count: number;
    packing_count: number;
}

interface DashboardStats {
    period_orders?: number;
    period_revenue?: number;
    shipped_orders?: number;
    shipped_revenue?: number;
    prev_orders?: number;
    prev_revenue?: number;
    today_orders?: number;
    today_revenue?: number;
    mtd_orders?: number;
    mtd_revenue?: number;
    status_counts?: Record<string, number>;
    channel_stats?: Record<string, number>;
    sales_trend?: SalesTrendItem[];
    top_products?: TopProductItem[];
    platform_breakdown?: PlatformStats[];
    filter_info?: {
        start_date: string;
        end_date: string;
        period_days: number;
    };
}

type DatePreset = 'today' | 'yesterday' | 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'this_year' | 'last_year' | 'custom';

const Dashboard: React.FC = () => {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [datePreset, setDatePreset] = useState<DatePreset>('this_month');
    const [startDate, setStartDate] = useState<string>('');
    const [endDate, setEndDate] = useState<string>('');

    const getDateRange = React.useCallback((preset: DatePreset): { start: string; end: string } => {
        const today = new Date();
        // Fixed: Use local date formatting to prevent UTC conversion shift
        const formatDate = (d: Date) => {
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };

        switch (preset) {
            case 'today':
                return { start: formatDate(today), end: formatDate(today) };
            case 'yesterday': {
                const yesterday = new Date(today);
                yesterday.setDate(yesterday.getDate() - 1);
                return { start: formatDate(yesterday), end: formatDate(yesterday) };
            }
            case 'this_week': {
                const weekStart = new Date(today);
                weekStart.setDate(today.getDate() - today.getDay());
                return { start: formatDate(weekStart), end: formatDate(today) };
            }
            case 'last_week': {
                const lastWeekEnd = new Date(today);
                lastWeekEnd.setDate(today.getDate() - today.getDay() - 1);
                const lastWeekStart = new Date(lastWeekEnd);
                lastWeekStart.setDate(lastWeekEnd.getDate() - 6);
                return { start: formatDate(lastWeekStart), end: formatDate(lastWeekEnd) };
            }
            case 'this_month': {
                const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
                return { start: formatDate(monthStart), end: formatDate(today) };
            }
            case 'last_month': {
                const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
                const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                return { start: formatDate(lastMonthStart), end: formatDate(lastMonthEnd) };
            }
            case 'this_year': {
                const yearStart = new Date(today.getFullYear(), 0, 1);
                return { start: formatDate(yearStart), end: formatDate(today) };
            }
            case 'custom':
                return { start: startDate, end: endDate };
            default:
                return { start: formatDate(today), end: formatDate(today) };
        }
    }, [startDate, endDate]);

    const fetchStats = React.useCallback(() => {
        setLoading(true);
        const { start, end } = getDateRange(datePreset);
        api.get('/dashboard/stats', { params: { start_date: start, end_date: end } })
            .then(res => {
                setStats(res.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Fetch stats error:", err);
                setLoading(false);
            });
    }, [datePreset, getDateRange]);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (datePreset === 'custom') {
                if (startDate && endDate) {
                    fetchStats();
                }
            } else {
                fetchStats();
            }
        }, 0);
        return () => clearTimeout(timer);
    }, [fetchStats, datePreset, startDate, endDate]);

    const formatNumber = (num: number) => new Intl.NumberFormat('th-TH').format(num);
    const formatCurrency = (num: number) => new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' }).format(num);

    const calcChange = (current: number, prev: number): { pct: number; direction: 'up' | 'down' | 'same' } => {
        if (prev === 0) return { pct: 0, direction: 'same' };
        const pct = ((current - prev) / prev) * 100;
        return { pct: Math.abs(pct), direction: pct > 0 ? 'up' : pct < 0 ? 'down' : 'same' };
    };

    const breadcrumb = (
        <li className="breadcrumb-item active" aria-current="page">Dashboard</li>
    );

    // Chart Data
    const salesChartData = {
        labels: stats?.sales_trend?.map(d => d.date) || [],
        datasets: [{
            label: 'ยอดขาย (บาท)',
            data: stats?.sales_trend?.map(d => d.revenue) || [],
            backgroundColor: 'rgba(13, 110, 253, 0.7)',
            borderRadius: 4,
            barThickness: 30
        }]
    };

    const channelColors: Record<string, string> = {
        'tiktok': '#000000',
        'shopee': '#EE4D2D',
        'lazada': '#0F146D',
        'facebook': '#1877F2',
        'line': '#00B900',
        'manual': '#6c757d'
    };

    const channelLabels = Object.keys(stats?.channel_stats || {});
    const channelChartData = {
        labels: channelLabels,
        datasets: [{
            data: Object.values(stats?.channel_stats || {}),
            backgroundColor: channelLabels.map(c => channelColors[c.toLowerCase()] || '#adb5bd'),
            borderWidth: 0
        }]
    };

    const presetLabels: Record<DatePreset, string> = {
        today: 'วันนี้',
        yesterday: 'เมื่อวาน',
        this_week: 'สัปดาห์นี้',
        last_week: 'สัปดาห์ที่แล้ว',
        this_month: 'เดือนนี้',
        last_month: 'เดือนที่แล้ว',
        this_year: 'ปีนี้',
        last_year: 'ปีที่แล้ว',
        custom: 'กำหนดเอง'
    };

    const orderChange = calcChange(stats?.period_orders || 0, stats?.prev_orders || 0);
    const revenueChange = calcChange(stats?.period_revenue || 0, stats?.prev_revenue || 0);

    return (
        <Layout
            title="Dashboard"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2 align-items-center">
                    <select
                        className="form-select form-select-sm"
                        value={datePreset}
                        onChange={(e) => setDatePreset(e.target.value as DatePreset)}
                        style={{ width: 'auto' }}
                    >
                        {Object.entries(presetLabels).map(([key, label]) => (
                            <option key={key} value={key}>{label}</option>
                        ))}
                    </select>
                    {datePreset === 'custom' && (
                        <>
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                style={{ width: 'auto' }}
                            />
                            <span className="text-muted">ถึง</span>
                            <input
                                type="date"
                                className="form-control form-control-sm"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                style={{ width: 'auto' }}
                            />
                        </>
                    )}
                    <button className="btn btn-outline-primary btn-sm" onClick={fetchStats} disabled={loading}>
                        <i className="bi bi-arrow-clockwise me-1"></i> รีเฟรช
                    </button>
                </div>
            }
        >
            {/* Key Metrics Row */}
            <div className="row g-3 mb-4">
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-start">
                                <div>
                                    <div className="text-muted small mb-1">ออเดอร์ ({presetLabels[datePreset]})</div>
                                    <div className="fs-2 fw-bold text-primary">{stats ? formatNumber(stats.period_orders || 0) : '-'}</div>
                                    {orderChange.direction !== 'same' && stats?.prev_orders !== undefined && (
                                        <div className={`small ${orderChange.direction === 'up' ? 'text-success' : 'text-danger'}`}>
                                            <i className={`bi bi-arrow-${orderChange.direction}`}></i> {orderChange.pct.toFixed(1)}%
                                        </div>
                                    )}
                                </div>
                                <div className="p-2 bg-primary bg-opacity-10 rounded">
                                    <i className="bi bi-cart-check text-primary fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-start">
                                <div>
                                    <div className="text-muted small mb-1">ยอดขาย ({presetLabels[datePreset]})</div>
                                    <div className="fs-2 fw-bold text-success">{stats ? formatCurrency(stats.period_revenue || 0) : '-'}</div>
                                    {revenueChange.direction !== 'same' && stats?.prev_revenue !== undefined && (
                                        <div className={`small ${revenueChange.direction === 'up' ? 'text-success' : 'text-danger'}`}>
                                            <i className={`bi bi-arrow-${revenueChange.direction}`}></i> {revenueChange.pct.toFixed(1)}%
                                        </div>
                                    )}
                                </div>
                                <div className="p-2 bg-success bg-opacity-10 rounded">
                                    <i className="bi bi-currency-dollar text-success fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-start">
                                <div>
                                    <div className="text-muted small mb-1">รอแพ็ค (PAID)</div>
                                    <div className="fs-2 fw-bold text-warning">{stats ? formatNumber(stats.status_counts?.PAID || 0) : '-'}</div>
                                </div>
                                <div className="p-2 bg-warning bg-opacity-10 rounded">
                                    <i className="bi bi-box-seam text-warning fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-sm-6 col-lg-3">
                    <div className="card h-100 border-0 shadow-sm border-start border-4 border-success">
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-start">
                                <div>
                                    <div className="text-muted small mb-1">ส่งออกจริง ({presetLabels[datePreset]})</div>
                                    <div className="fs-2 fw-bold text-success">{stats ? formatNumber(stats.shipped_orders || 0) : '-'}</div>
                                    <div className="small text-muted">
                                        {stats ? formatCurrency(stats.shipped_revenue || 0) : '-'}
                                    </div>
                                </div>
                                <div className="p-2 bg-success bg-opacity-10 rounded">
                                    <i className="bi bi-truck text-success fs-4"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Status Overview Row */}
            <div className="row g-3 mb-4">
                {[
                    { status: 'NEW', label: 'รอตรวจสอบ', color: 'secondary', icon: 'bi-hourglass' },
                    { status: 'PAID', label: 'รอแพ็ค', color: 'warning', icon: 'bi-box-seam' },
                    { status: 'PACKING', label: 'กำลังแพ็ค', color: 'info', icon: 'bi-box2' },
                    { status: 'SHIPPED', label: 'จัดส่งแล้ว', color: 'primary', icon: 'bi-truck' },
                    { status: 'DELIVERED', label: 'สำเร็จ', color: 'success', icon: 'bi-check-circle' },
                    { status: 'CANCELLED', label: 'ยกเลิก', color: 'danger', icon: 'bi-x-circle' }
                ].map((item) => (
                    <div className="col-6 col-md-4 col-lg-2" key={item.status}>
                        <Link to={`/orders?status=${item.status}`} className="text-decoration-none">
                            <div className={`card h-100 border-0 shadow-sm hover-shadow`}>
                                <div className="card-body p-3 text-center">
                                    <div className={`d-inline-flex align-items-center justify-content-center p-2 rounded-circle bg-${item.color} bg-opacity-10 mb-2`}>
                                        <i className={`bi ${item.icon} text-${item.color} fs-5`}></i>
                                    </div>
                                    <h6 className="text-muted small mb-1">{item.label}</h6>
                                    <div className={`fs-4 fw-bold text-${item.color}`}>
                                        {formatNumber(stats?.status_counts?.[item.status] || 0)}
                                    </div>
                                </div>
                            </div>
                        </Link>
                    </div>
                ))}
            </div>

            {/* Platform Breakdown Row */}
            {stats?.platform_breakdown && stats.platform_breakdown.length > 0 && (
                <div className="row g-3 mb-4">
                    {stats.platform_breakdown.map((p) => {
                        const color = channelColors[p.platform.toLowerCase()] || '#6c757d';
                        return (
                            <div className="col-sm-6 col-md-3" key={p.platform}>
                                <div className="card h-100 border-0 shadow-sm" style={{ borderLeft: `4px solid ${color}` }}>
                                    <div className="card-body">
                                        <div className="d-flex justify-content-between align-items-center mb-2">
                                            <h6 className="mb-0 text-uppercase fw-bold" style={{ color: color }}>
                                                {p.platform === 'manual' ? 'Manual / POS' : p.platform}
                                            </h6>
                                            <span className="badge rounded-pill bg-light text-dark border">
                                                {formatNumber(p.count)} ออเดอร์
                                            </span>
                                        </div>
                                        <div className="fs-4 fw-bold mb-2">{formatCurrency(p.revenue)}</div>

                                        {/* Operational Stats Badges */}
                                        <div className="d-flex gap-2">
                                            {(p.paid_count > 0 || (p.platform !== 'manual' && p.packing_count > 0)) && (
                                                <>
                                                    {p.paid_count > 0 && (
                                                        <span className="badge bg-warning text-dark border border-warning bg-opacity-25" title="รอแพ็ค">
                                                            <i className="bi bi-box-seam me-1"></i>{formatNumber(p.paid_count)}
                                                        </span>
                                                    )}
                                                    {p.packing_count > 0 && (
                                                        <span className="badge bg-info text-dark border border-info bg-opacity-25" title="รอส่ง">
                                                            <i className="bi bi-truck me-1"></i>{formatNumber(p.packing_count)}
                                                        </span>
                                                    )}
                                                </>
                                            )}
                                            {p.paid_count === 0 && p.packing_count === 0 && (
                                                <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25">
                                                    <i className="bi bi-check-circle me-1"></i>All Clear
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Charts Row */}
            <div className="row g-3 mb-4">
                <div className="col-lg-8">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-header bg-white border-0 py-3">
                            <h6 className="mb-0 fw-bold"><i className="bi bi-bar-chart-line me-2"></i>แนวโน้มยอดขาย ({stats?.filter_info?.period_days || 0} วัน)</h6>
                        </div>
                        <div className="card-body">
                            <Bar
                                data={salesChartData}
                                options={{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: { legend: { display: false } },
                                    scales: {
                                        y: { beginAtZero: true, grid: { tickBorderDash: [2, 2] } },
                                        x: { grid: { display: false } }
                                    }
                                }}
                                height={200}
                            />
                        </div>
                    </div>
                </div>
                <div className="col-lg-4">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-header bg-white border-0 py-3">
                            <h6 className="mb-0 fw-bold"><i className="bi bi-pie-chart me-2"></i>สัดส่วนช่องทาง</h6>
                        </div>
                        <div className="card-body d-flex align-items-center justify-content-center">
                            <div style={{ width: '100%', maxWidth: '220px' }}>
                                {channelLabels.length > 0 ? (
                                    <Doughnut
                                        data={channelChartData}
                                        options={{
                                            responsive: true,
                                            plugins: {
                                                legend: {
                                                    position: 'bottom',
                                                    labels: { usePointStyle: true, boxWidth: 8 }
                                                }
                                            },
                                            cutout: '70%'
                                        }}
                                    />
                                ) : (
                                    <div className="text-center text-muted">ไม่มีข้อมูล</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Row */}
            <div className="row g-3">
                <div className="col-lg-8">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-header bg-white border-0 py-3 d-flex justify-content-between align-items-center">
                            <h6 className="mb-0 fw-bold"><i className="bi bi-trophy me-2"></i>สินค้าขายดี 5 อันดับแรก</h6>
                            <Link to="/products" className="btn btn-sm btn-light text-muted">ดูทั้งหมด</Link>
                        </div>
                        <div className="card-body p-0">
                            <div className="table-responsive">
                                <table className="table table-hover align-middle mb-0">
                                    <thead className="bg-light">
                                        <tr>
                                            <th className="ps-4">สินค้า</th>
                                            <th className="text-center">จำนวนขาย</th>
                                            <th className="text-end pe-4">ยอดขายรวม</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {stats?.top_products && stats.top_products.length > 0 ? (
                                            stats.top_products.map((p, index) => (
                                                <tr key={`product-${index}`}>
                                                    <td className="ps-4">
                                                        <div className="d-flex align-items-center">
                                                            <span className="badge bg-light text-dark me-2 border">{index + 1}</span>
                                                            <div>
                                                                <div className="fw-bold text-dark">{p.product_name || '-'}</div>
                                                                <div className="small text-muted text-mono">{p.sku}</div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="text-center text-mono">{formatNumber(p.total_qty)}</td>
                                                    <td className="text-end pe-4 text-mono text-dark fw-bold">{formatCurrency(p.total_sales)}</td>
                                                </tr>
                                            ))
                                        ) : (
                                            <tr><td colSpan={3} className="text-center py-4 text-muted">ยังไม่มีข้อมูลสินค้าขายดี</td></tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="col-lg-4">
                    <div className="card h-100 border-0 shadow-sm">
                        <div className="card-header bg-white border-0 py-3">
                            <h6 className="mb-0 fw-bold"><i className="bi bi-list-check me-2"></i>สิ่งที่ต้องทำ</h6>
                        </div>
                        <div className="card-body">
                            <div className="list-group list-group-flush">
                                <Link to="/orders?status=PAID" className="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3">
                                    <div>
                                        <i className="bi bi-box-seam text-warning me-2"></i>
                                        รอแพ็คสินค้า (PAID)
                                    </div>
                                    <span className="badge bg-warning text-dark rounded-pill">{formatNumber(stats?.status_counts?.PAID || 0)}</span>
                                </Link>
                                <Link to="/packing" className="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3">
                                    <div>
                                        <i className="bi bi-truck text-info me-2"></i>
                                        กำลังแพ็ค/รอส่ง (PACKING)
                                    </div>
                                    <span className="badge bg-info text-dark rounded-pill">{formatNumber(stats?.status_counts?.PACKING || 0)}</span>
                                </Link>
                                <Link to="/orders?status=NEW" className="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3">
                                    <div>
                                        <i className="bi bi-hourglass text-muted me-2"></i>
                                        ออเดอร์ใหม่ (NEW)
                                    </div>
                                    <span className="badge bg-secondary rounded-pill">{formatNumber(stats?.status_counts?.NEW || 0)}</span>
                                </Link>
                                <Link to="/orders/create" className="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-3">
                                    <div className="text-primary fw-bold">
                                        <i className="bi bi-plus-circle me-2"></i>
                                        สร้างออเดอร์ใหม่
                                    </div>
                                    <i className="bi bi-chevron-right text-muted small"></i>
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Dashboard;
