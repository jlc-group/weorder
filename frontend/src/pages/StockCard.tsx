import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';

interface StockMovement {
    id: string;
    date: string;
    movement_type: string;
    quantity: number;
    effect: number;
    balance: number;
    reference_type: string;
    reference_id: string;
    note: string;
}

interface LocationBalance {
    location_name: string;
    quantity: number;
    reserved: number;
    available: number;
}

interface StockCardData {
    sku: string;
    product_name: string;
    product_id: string;
    current_stock: {
        on_hand: number;
        reserved: number;
        available: number;
    };
    location_balances?: LocationBalance[];
    movements_count: number;
    movements: StockMovement[];
}

interface Warehouse {
    id: string;
    name: string;
    code: string;
}

const StockCard: React.FC = () => {
    const { sku } = useParams<{ sku: string }>();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const [data, setData] = useState<StockCardData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);



    // Filters
    const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
    const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>(searchParams.get('warehouse_id') || '');
    const [startDate, setStartDate] = useState<string>(searchParams.get('start') || '');
    const [endDate, setEndDate] = useState<string>(searchParams.get('end') || '');
    const [filterType, setFilterType] = useState<string>('');

    const fetchStockCard = useCallback(async () => {
        if (!sku) return;

        setLoading(true);
        setError(null);

        try {
            const params: Record<string, string> = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            if (selectedWarehouseId) params.warehouse_id = selectedWarehouseId;

            const { data: result } = await api.get(`/stock/card/${encodeURIComponent(sku)}`, { params });
            setData(result);
        } catch (err: unknown) {
            console.error('Failed to load stock card:', err);
            setError((err as Error).message || 'ไม่สามารถโหลดข้อมูลได้');
        } finally {
            setLoading(false);
        }
    }, [sku, startDate, endDate, selectedWarehouseId]);

    useEffect(() => {
        // Fetch warehouses
        api.get('/master/warehouses').then(res => setWarehouses(res.data)).catch(console.error);
    }, []);

    useEffect(() => {
        fetchStockCard();
    }, [fetchStockCard]);

    // Filter movements by type
    const filteredMovements = data?.movements.filter(m =>
        !filterType || m.movement_type === filterType
    ) || [];

    // Export to CSV
    const handleExport = () => {
        if (!data) return;

        const headers = ['Date', 'Type', 'Qty', 'Effect', 'Balance', 'Reference', 'Note'];
        const rows = data.movements.map(m => [
            m.date ? new Date(m.date).toLocaleString('th-TH') : '',
            m.movement_type,
            m.quantity,
            m.effect > 0 ? `+${m.effect}` : m.effect,
            m.balance,
            `${m.reference_type || ''} ${m.reference_id || ''}`.trim(),
            `"${(m.note || '').replace(/"/g, '""')}"`
        ]);

        const csvContent = "data:text/csv;charset=utf-8,"
            + headers.join(",") + "\n"
            + rows.map(r => r.join(",")).join("\n");

        const link = document.createElement("a");
        link.setAttribute("href", encodeURI(csvContent));
        link.setAttribute("download", `stock_card_${sku}_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const getMovementBadge = (type: string) => {
        const types: Record<string, { color: string; label: string; icon: string }> = {
            'IN': { color: 'success', label: 'รับเข้า', icon: 'bi-arrow-down-circle' },
            'OUT': { color: 'danger', label: 'จ่ายออก', icon: 'bi-arrow-up-circle' },
            'RESERVE': { color: 'warning', label: 'จอง', icon: 'bi-lock' },
            'RELEASE': { color: 'info', label: 'ปลดจอง', icon: 'bi-unlock' },
            'ADJUST': { color: 'secondary', label: 'ปรับปรุง', icon: 'bi-pencil-square' }
        };
        const t = types[type] || { color: 'dark', label: type, icon: 'bi-question-circle' };
        return (
            <span className={`badge bg-${t.color}`}>
                <i className={`bi ${t.icon} me-1`}></i>
                {t.label}
            </span>
        );
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item">
                <a href="/stock" onClick={(e) => { e.preventDefault(); navigate('/stock'); }}>Stock</a>
            </li>
            <li className="breadcrumb-item active">Stock Card: {sku}</li>
        </>
    );

    return (
        <Layout
            title={`Stock Card: ${sku || ''}`}
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <button className="btn btn-outline-primary" onClick={fetchStockCard} disabled={loading}>
                        <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                    </button>
                    <button className="btn btn-success" onClick={handleExport} disabled={!data}>
                        <i className="bi bi-file-earmark-excel me-2"></i>Export CSV
                    </button>
                </div>
            }
        >
            {error && (
                <div className="alert alert-danger">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    {error}
                </div>
            )}

            {data && (
                <>
                    {/* Warehouse Filter in Product Info to show context */}
                    <div className="row g-4 mb-4">
                        <div className="col-md-4">
                            <div className="card border-0 shadow-sm h-100">
                                <div className="card-body">
                                    <h5 className="card-title text-primary">{data.sku}</h5>
                                    <p className="text-muted mb-3">{data.product_name}</p>

                                    <label className="form-label small text-muted">แสดงข้อมูลตามคลัง:</label>
                                    <select
                                        className="form-select form-select-sm"
                                        value={selectedWarehouseId}
                                        onChange={(e) => setSelectedWarehouseId(e.target.value)}
                                    >
                                        <option value="">ทุกคลังสินค้า (รวม)</option>
                                        {warehouses.map(w => (
                                            <option key={w.id} value={w.id}>{w.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-8">
                            <div className="row g-3">
                                <div className="col-4">
                                    <div className="card bg-primary text-white h-100">
                                        <div className="card-body text-center py-3">
                                            <h3 className="fw-bold mb-0">{data.current_stock.on_hand.toLocaleString()}</h3>
                                            <small className="opacity-75">On Hand</small>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-4">
                                    <div className="card bg-warning text-dark h-100">
                                        <div className="card-body text-center py-3">
                                            <h3 className="fw-bold mb-0">{data.current_stock.reserved.toLocaleString()}</h3>
                                            <small className="opacity-75">Reserved</small>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-4">
                                    <div className="card bg-success text-white h-100">
                                        <div className="card-body text-center py-3">
                                            <h3 className="fw-bold mb-0">{data.current_stock.available.toLocaleString()}</h3>
                                            <small className="opacity-75">Available</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Location Breakdown (Only if warehouse selected and data exists) */}
                    {selectedWarehouseId && data.location_balances && data.location_balances.length > 0 && (
                        <div className="card border-0 shadow-sm mb-4">
                            <div className="card-header bg-white py-2">
                                <h6 className="mb-0"><i className="bi bi-geo-alt me-2"></i>Location Breakdown</h6>
                            </div>
                            <div className="table-responsive">
                                <table className="table table-sm table-hover mb-0">
                                    <thead className="table-light">
                                        <tr>
                                            <th className="ps-4">Location</th>
                                            <th className="text-end">On Hand</th>
                                            <th className="text-end">Reserved</th>
                                            <th className="text-end pe-4">Available</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.location_balances.map((loc, idx) => (
                                            <tr key={idx}>
                                                <td className="ps-4 fw-bold">{loc.location_name}</td>
                                                <td className="text-end">{loc.quantity}</td>
                                                <td className="text-end text-warning">{loc.reserved}</td>
                                                <td className="text-end pe-4 fw-bold text-success">{loc.available}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Filters */}
                    <div className="card border-0 shadow-sm mb-4">
                        <div className="card-body py-3">
                            <div className="row g-3 align-items-end">
                                <div className="col-md-3">
                                    <label className="form-label small">จากวันที่</label>
                                    <input
                                        type="date"
                                        className="form-control"
                                        value={startDate}
                                        onChange={(e) => setStartDate(e.target.value)}
                                    />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label small">ถึงวันที่</label>
                                    <input
                                        type="date"
                                        className="form-control"
                                        value={endDate}
                                        onChange={(e) => setEndDate(e.target.value)}
                                    />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label small">ประเภท</label>
                                    <select
                                        className="form-select"
                                        value={filterType}
                                        onChange={(e) => setFilterType(e.target.value)}
                                    >
                                        <option value="">ทั้งหมด</option>
                                        <option value="IN">รับเข้า (IN)</option>
                                        <option value="OUT">จ่ายออก (OUT)</option>
                                        <option value="RESERVE">จอง (RESERVE)</option>
                                        <option value="RELEASE">ปลดจอง (RELEASE)</option>
                                        <option value="ADJUST">ปรับปรุง (ADJUST)</option>
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <button className="btn btn-primary w-100" onClick={fetchStockCard}>
                                        <i className="bi bi-search me-2"></i>โหลดข้อมูล
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Movements Table */}
                    <div className="card border-0 shadow-sm">
                        <div className="card-header bg-white py-3 d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">
                                <i className="bi bi-list-ul me-2"></i>
                                ประวัติการเคลื่อนไหว
                            </h5>
                            <span className="badge bg-secondary">{filteredMovements.length} รายการ</span>
                        </div>
                        <div className="card-body p-0">
                            <div className="table-responsive">
                                <table className="table table-hover align-middle mb-0">
                                    <thead className="bg-light">
                                        <tr>
                                            <th className="ps-4">วันที่/เวลา</th>
                                            <th>ประเภท</th>
                                            <th className="text-center">จำนวน</th>
                                            <th className="text-center">ผลกระทบ</th>
                                            <th className="text-center">ยอดคงเหลือ</th>
                                            <th>อ้างอิง</th>
                                            <th className="pe-4">หมายเหตุ</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {loading ? (
                                            <tr>
                                                <td colSpan={7} className="text-center py-5">
                                                    <div className="spinner-border text-primary"></div>
                                                    <div className="mt-2 text-muted">กำลังโหลด...</div>
                                                </td>
                                            </tr>
                                        ) : filteredMovements.length === 0 ? (
                                            <tr>
                                                <td colSpan={7} className="text-center py-5 text-muted">
                                                    <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                                                    ไม่พบรายการ
                                                </td>
                                            </tr>
                                        ) : (
                                            filteredMovements.map((m) => (
                                                <tr key={m.id}>
                                                    <td className="ps-4 small">
                                                        {m.date ? new Date(m.date).toLocaleString('th-TH') : '-'}
                                                    </td>
                                                    <td>{getMovementBadge(m.movement_type)}</td>
                                                    <td className="text-center font-monospace">{m.quantity}</td>
                                                    <td className={`text-center font-monospace fw-bold ${m.effect > 0 ? 'text-success' : 'text-danger'}`}>
                                                        {m.effect > 0 ? '+' : ''}{m.effect}
                                                    </td>
                                                    <td className="text-center font-monospace fw-bold">{m.balance}</td>
                                                    <td className="small text-muted">
                                                        {m.reference_type && (
                                                            <span className="badge bg-light text-dark me-1">{m.reference_type}</span>
                                                        )}
                                                        {m.reference_id && (
                                                            <span className="text-primary">{m.reference_id.slice(0, 8)}</span>
                                                        )}
                                                    </td>
                                                    <td className="pe-4 small text-muted" style={{ maxWidth: '200px' }}>
                                                        {m.note || '-'}
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </Layout>
    );
};

export default StockCard;
