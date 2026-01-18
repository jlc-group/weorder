import React, { useEffect, useState, useCallback } from 'react';
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

const SalesProfitability: React.FC = () => {
    const [orders, setOrders] = useState<OrderProfit[]>([]);
    const [loading, setLoading] = useState(true);
    const [startDate, setStartDate] = useState<string>(() => {
        const d = new Date();
        d.setDate(1);
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState<string>(() => {
        const d = new Date();
        return d.toISOString().split('T')[0];
    });
    const [sortField, setSortField] = useState<keyof OrderProfit>('date');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    const fetchProfitability = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await api.get('/finance/profitability', {
                params: { start_date: startDate, end_date: endDate }
            });
            setOrders(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [startDate, endDate]);

    useEffect(() => {
        fetchProfitability();
    }, [fetchProfitability]);

    const formatCurrency = (val: number) => new Intl.NumberFormat('th-TH').format(val);

    const sortedOrders = [...orders].sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];
        if (valA < valB) return sortDir === 'asc' ? -1 : 1;
        if (valA > valB) return sortDir === 'asc' ? 1 : -1;
        return 0;
    });

    const handleSort = (field: keyof OrderProfit) => {
        if (sortField === field) {
            setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir('desc');
        }
    };

    return (
        <Layout
            title="Sales Profitability (Unit Economics)"
            breadcrumb={<li className="breadcrumb-item active">Profitability</li>}
            actions={
                <div className="d-flex gap-2">
                    <input type="date" className="form-control" value={startDate} onChange={e => setStartDate(e.target.value)} />
                    <input type="date" className="form-control" value={endDate} onChange={e => setEndDate(e.target.value)} />
                    <button className="btn btn-primary" onClick={fetchProfitability}>Refresh</button>
                </div>
            }
        >
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover mb-0 align-middle small">
                            <thead className="bg-light">
                                <tr>
                                    <th onClick={() => handleSort('date')} role="button">Date</th>
                                    <th onClick={() => handleSort('order_number')} role="button">Order #</th>
                                    <th onClick={() => handleSort('platform')} role="button">Platform</th>
                                    <th>Items</th>
                                    <th className="text-end" onClick={() => handleSort('revenue')} role="button">Revenue</th>
                                    <th className="text-end" onClick={() => handleSort('fees')} role="button">Est. Fees (12%)</th>
                                    <th className="text-end" onClick={() => handleSort('cogs')} role="button">COGS</th>
                                    <th className="text-end fw-bold" onClick={() => handleSort('net_profit')} role="button">Net Profit</th>
                                    <th className="text-end" onClick={() => handleSort('margin_percent')} role="button">% Margin</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && <tr><td colSpan={9} className="text-center py-4">Loading...</td></tr>}
                                {!loading && sortedOrders.length === 0 && <tr><td colSpan={9} className="text-center py-4">No data</td></tr>}
                                {sortedOrders.map(o => (
                                    <tr key={o.order_number}>
                                        <td>{o.date}</td>
                                        <td>{o.order_number}</td>
                                        <td><span className={`badge bg-${o.platform === 'shopee' ? 'warning' : 'dark'}`}>{o.platform}</span></td>
                                        <td className="text-truncate" style={{ maxWidth: '200px' }} title={o.items}>{o.items}</td>
                                        <td className="text-end">{formatCurrency(o.revenue)}</td>
                                        <td className="text-end text-danger">{formatCurrency(o.fees)}</td>
                                        <td className="text-end text-muted">{formatCurrency(o.cogs)}</td>
                                        <td className={`text-end fw-bold ${o.net_profit > 0 ? 'text-success' : 'text-danger'}`}>
                                            {formatCurrency(o.net_profit)}
                                        </td>
                                        <td className="text-end">
                                            <span className={`badge ${o.margin_percent > 20 ? 'bg-success' : o.margin_percent > 0 ? 'bg-warning text-dark' : 'bg-danger'}`}>
                                                {o.margin_percent.toFixed(1)}%
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default SalesProfitability;
