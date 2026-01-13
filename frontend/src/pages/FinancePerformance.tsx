import React, { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
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
import { Pie, Bar } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
);

interface PlatformPerformance {
    platform: string;
    revenue: number;
    fees: number;
    fee_details: Record<string, number>;
    net_income: number;
    cogs: number;
    net_profit: number;
}

interface PerformanceData {
    period: {
        start: string;
        end: string;
    };
    summary: {
        total_revenue: number;
        total_fees: number;
        total_net_income: number;
        total_cogs: number;
        total_net_profit: number;
    };
    platforms: PlatformPerformance[];
}

const FinancePerformance: React.FC = () => {
    const [data, setData] = useState<PerformanceData | null>(null);
    const [loading, setLoading] = useState(true);
    const [startDate, setStartDate] = useState<string>(() => {
        const d = new Date();
        d.setDate(1); // First of month
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState<string>(() => {
        const d = new Date();
        return d.toISOString().split('T')[0];
    });

    const fetchPerformance = useCallback(async () => {
        setLoading(true);
        try {
            const { data: perfData } = await api.get('/finance/performance', {
                params: { start_date: startDate, end_date: endDate }
            });
            setData(perfData);
        } catch (e) {
            console.error('Failed to fetch performance data:', e);
        } finally {
            setLoading(false);
        }
    }, [startDate, endDate]);

    useEffect(() => {
        fetchPerformance();
    }, [fetchPerformance]);

    const formatCurrency = (num: number) =>
        new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' }).format(num);

    const formatNumber = (num: number) =>
        new Intl.NumberFormat('th-TH').format(num);

    // Chart Data: Fee Component Breakdown
    const feeLabels = data ? Object.keys(data.platforms.reduce((acc, p) => ({ ...acc, ...p.fee_details }), {})) : [];
    const feeData = data ? feeLabels.map(label =>
        data.platforms.reduce((sum, p) => sum + Math.abs(p.fee_details[label] || 0), 0)
    ) : [];

    const feeBreakdownChart = {
        labels: feeLabels.map(l => l.replace('_', ' ')),
        datasets: [{
            data: feeData,
            backgroundColor: [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
            ],
            borderWidth: 1
        }]
    };

    // Chart Data: Platform Comparison
    const platLabels = data?.platforms.map(p => p.platform) || [];
    const platRevenue = data?.platforms.map(p => p.revenue) || [];
    const platProfit = data?.platforms.map(p => p.net_profit) || [];

    const platComparisonChart = {
        labels: platLabels.map(l => l.toUpperCase()),
        datasets: [
            {
                label: 'รายรับรวม',
                data: platRevenue,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
            },
            {
                label: 'กำไรสุทธิ',
                data: platProfit,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
            }
        ]
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item"><a href="/finance" className="text-decoration-none">Finance</a></li>
            <li className="breadcrumb-item active">Performance</li>
        </>
    );

    return (
        <Layout
            title="สรุปผลประกอบการทางการเงิน"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <input
                        type="date"
                        className="form-control form-control-sm"
                        value={startDate}
                        onChange={e => setStartDate(e.target.value)}
                    />
                    <input
                        type="date"
                        className="form-control form-control-sm"
                        value={endDate}
                        onChange={e => setEndDate(e.target.value)}
                    />
                    <button className="btn btn-sm btn-primary" onClick={fetchPerformance}>รีเฟรช</button>
                </div>
            }
        >
            {loading ? (
                <div className="text-center py-5"><div className="spinner-border text-primary"></div></div>
            ) : !data ? (
                <div className="alert alert-info">ไม่พบข้อมูลในช่วงเวลาที่ระบุ</div>
            ) : (
                <div className="row g-3">
                    {/* Summary Cards */}
                    <div className="col-md-3">
                        <div className="card border-0 shadow-sm h-100">
                            <div className="card-body">
                                <h6 className="text-muted small mb-1">รายรับรวม (Gross Revenue)</h6>
                                <div className="fs-3 fw-bold text-primary">{formatCurrency(data.summary.total_revenue)}</div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-3">
                        <div className="card border-0 shadow-sm h-100">
                            <div className="card-body">
                                <h6 className="text-muted small mb-1">ค่าธรรมเนียมรวม (Platform Fees)</h6>
                                <div className="fs-3 fw-bold text-danger">{formatCurrency(Math.abs(data.summary.total_fees))}</div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-3">
                        <div className="card border-0 shadow-sm h-100">
                            <div className="card-body">
                                <h6 className="text-muted small mb-1">ต้นทุนสินค้ารวม (COGS)</h6>
                                <div className="fs-3 fw-bold text-warning">{formatCurrency(data.summary.total_cogs)}</div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-3">
                        <div className="card border-0 shadow-sm h-100 border-start border-4 border-success">
                            <div className="card-body">
                                <h6 className="text-muted small mb-1">กำไรสุทธิ (Net Profit)</h6>
                                <div className={`fs-3 fw-bold ${data.summary.total_net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                    {formatCurrency(data.summary.total_net_profit)}
                                </div>
                                <div className="small text-muted mt-1">
                                    Margin: {((data.summary.total_net_profit / data.summary.total_revenue) * 100).toFixed(1)}%
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Charts Row */}
                    <div className="col-lg-7">
                        <div className="card border-0 shadow-sm h-100">
                            <div className="card-header bg-white border-0 py-3">
                                <h6 className="mb-0 fw-bold"><i className="bi bi-bar-chart-line me-2"></i>เปรียบเทียบผลงานแต่ละแพลตฟอร์ม</h6>
                            </div>
                            <div className="card-body">
                                <Bar data={platComparisonChart} options={{ responsive: true, maintainAspectRatio: false }} height={300} />
                            </div>
                        </div>
                    </div>
                    <div className="col-lg-5">
                        <div className="card border-0 shadow-sm h-100">
                            <div className="card-header bg-white border-0 py-3">
                                <h6 className="mb-0 fw-bold"><i className="bi bi-pie-chart me-2"></i>สัดส่วนค่าธรรมเนียม</h6>
                            </div>
                            <div className="card-body d-flex align-items-center justify-content-center">
                                <div style={{ width: '80%' }}>
                                    <Pie data={feeBreakdownChart} options={{ responsive: true }} />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Detailed Table */}
                    <div className="col-12">
                        <div className="card border-0 shadow-sm">
                            <div className="card-header bg-white border-0 py-3">
                                <h6 className="mb-0 fw-bold"><i className="bi bi-table me-2"></i>รายละเอียดรายแพลตฟอร์ม</h6>
                            </div>
                            <div className="card-body p-0">
                                <div className="table-responsive">
                                    <table className="table table-hover mb-0 align-middle">
                                        <thead className="bg-light">
                                            <tr>
                                                <th className="ps-4">แพลตฟอร์ม</th>
                                                <th className="text-end">รายรับรวม</th>
                                                <th className="text-end">ค่าธรรมเนียม</th>
                                                <th className="text-end">เงินโอนเข้าสุทธิ</th>
                                                <th className="text-end">ต้นทุน (COGS)</th>
                                                <th className="text-end pe-4">กำไรสุทธิ</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.platforms.map(p => (
                                                <tr key={p.platform}>
                                                    <td className="ps-4 fw-bold">{p.platform.toUpperCase()}</td>
                                                    <td className="text-end">{formatNumber(p.revenue)}</td>
                                                    <td className="text-end text-danger">{formatNumber(p.fees)}</td>
                                                    <td className="text-end fw-semibold">{formatNumber(p.net_income)}</td>
                                                    <td className="text-end text-muted">{formatNumber(p.cogs)}</td>
                                                    <td className={`text-end pe-4 fw-bold ${p.net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                                        {formatNumber(p.net_profit)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot className="table-light fw-bold">
                                            <tr>
                                                <td className="ps-4">รวมทั้งหมด</td>
                                                <td className="text-end">{formatNumber(data.summary.total_revenue)}</td>
                                                <td className="text-end text-danger">{formatNumber(data.summary.total_fees)}</td>
                                                <td className="text-end">{formatNumber(data.summary.total_net_income)}</td>
                                                <td className="text-end">{formatNumber(data.summary.total_cogs)}</td>
                                                <td className={`text-end pe-4 fs-5 ${data.summary.total_net_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                                                    {formatNumber(data.summary.total_net_profit)}
                                                </td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default FinancePerformance;
