import React, { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import type { StockSummary, StockMovement } from '../types';

// Daily Outbound types
interface OutboundItem {
    sku: string;
    product_name: string;
    total_quantity: number;
    order_count: number;
}

interface OutboundData {
    date: string;
    total_items: number;
    total_orders: number;
    items: OutboundItem[];
    platforms?: Record<string, { orders: number, items: number }>;
}

interface Warehouse {
    id: string;
    name: string;
    code: string;
}

const Stock: React.FC = () => {
    // Tab state
    const [activeTab, setActiveTab] = useState<'summary' | 'movements' | 'outbound'>('summary');

    // Stock Summary state
    const [summary, setSummary] = useState<StockSummary[]>([]);
    const [movements, setMovements] = useState<StockMovement[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    // Movements date filter state
    const [movementsStartDate, setMovementsStartDate] = useState(new Date().toISOString().split('T')[0]);
    const [movementsEndDate, setMovementsEndDate] = useState(new Date().toISOString().split('T')[0]);

    // Warehouse Filter
    const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
    const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>('');

    // Transfer Modal State
    const [showTransferModal, setShowTransferModal] = useState(false);
    const [transferForm, setTransferForm] = useState({
        sku: '',
        from_warehouse_id: '',
        to_warehouse_id: '',
        quantity: 1
    });

    // Daily Outbound state
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [outboundData, setOutboundData] = useState<OutboundData | null>(null);
    const [dateMode, setDateMode] = useState<'collection' | 'rts'>('collection');

    // Fetch warehouses
    useEffect(() => {
        api.get('/master/warehouses').then(res => {
            setWarehouses(res.data);
            if (res.data.length > 0) {
                setSelectedWarehouseId(res.data[0].id);
            }
        }).catch(err => console.error(err));
    }, []);

    // Fetch stock summary
    const fetchSummary = useCallback(async () => {
        setLoading(true);
        try {
            const params: any = {};
            if (selectedWarehouseId) params.warehouse_id = selectedWarehouseId;

            const res = await api.get('/stock/summary', { params });
            setSummary(res.data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, [selectedWarehouseId]);

    // Fetch stock movements
    const fetchMovements = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get('/stock/movements', {
                params: {
                    start_date: movementsStartDate,
                    end_date: movementsEndDate
                }
            });
            setMovements(res.data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, [movementsStartDate, movementsEndDate]);

    // Fetch daily outbound
    const fetchOutbound = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await api.get(`/report/daily-outbound`, {
                params: { date: selectedDate, date_mode: dateMode }
            });
            setOutboundData(data);
        } catch (e) {
            console.error('Failed to load outbound:', e);
        } finally {
            setLoading(false);
        }
    }, [selectedDate, dateMode]);

    useEffect(() => {
        if (activeTab === 'summary') fetchSummary();
        else if (activeTab === 'movements') fetchMovements();
        else if (activeTab === 'outbound') fetchOutbound();
    }, [activeTab, fetchSummary, fetchMovements, fetchOutbound]);

    // Filter summary by search term
    const filteredSummary = summary.filter(item =>
        item.sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.product_name?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Platform stat helper
    const getPlatformStat = (p: string) => {
        if (!outboundData?.platforms) return { orders: 0, items: 0 };
        return outboundData.platforms[p] || { orders: 0, items: 0 };
    };

    // Export CSV
    const handleExport = () => {
        if (!outboundData) return;
        const headers = ['SKU', 'Product Name', 'Quantity', 'Orders Count'];
        const rows = outboundData.items.map(item => [
            item.sku,
            `"${item.product_name.replace(/"/g, '""')}"`,
            item.total_quantity,
            item.order_count
        ]);
        const csvContent = "data:text/csv;charset=utf-8,"
            + headers.join(",") + "\n"
            + rows.map(e => e.join(",")).join("\n");
        const link = document.createElement("a");
        link.setAttribute("href", encodeURI(csvContent));
        link.setAttribute("download", `daily_outbound_${selectedDate}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleTransfer = async () => {
        if (!transferForm.sku || !transferForm.from_warehouse_id || !transferForm.to_warehouse_id || !transferForm.quantity) {
            alert('กรุณากรอกข้อมูลให้ครบถ้วน');
            return;
        }

        // Find product ID from SKU (Assuming SKU is unique and we can find it from summary list or need separate API)
        // For simplicity, let's assume we find it in summary list if loaded, or we need to fetch product ID by SKU.
        // Let's use the summary list for now.
        const product = summary.find(s => s.sku === transferForm.sku);
        if (!product) {
            alert('ไม่พบสินค้านี้ในระบบ (กรุณาโหลดหน้า Summary ให้ครบก่อน)');
            return;
        }

        if (transferForm.from_warehouse_id === transferForm.to_warehouse_id) {
            alert('คลังสินค้าต้นทางและปลายทางต้องไม่เหมือนกัน');
            return;
        }

        try {
            await api.post('/stock/transfer', {
                product_id: product.product_id,
                from_warehouse_id: transferForm.from_warehouse_id,
                to_warehouse_id: transferForm.to_warehouse_id,
                quantity: transferForm.quantity
            });
            alert('โอนย้ายสำเร็จ');
            setShowTransferModal(false);
            fetchSummary(); // Refresh
        } catch (e) {
            alert('เกิดข้อผิดพลาด: ' + (e as any).message);
        }
    };

    const breadcrumb = <li className="breadcrumb-item active">Stock</li>;

    // Calculate summary stats
    const totalOnHand = summary.reduce((acc, item) => acc + (item.on_hand || 0), 0);
    const totalAllocated = summary.reduce((acc, item) => acc + (item.allocated || 0), 0);
    const lowStockCount = summary.filter(item => (item.available || 0) < 10 && (item.available || 0) > 0).length;

    return (
        <Layout title="Stock Management" breadcrumb={breadcrumb} actions={
            <div className="d-flex gap-2">
                <button
                    className="btn btn-outline-secondary"
                    onClick={() => setShowTransferModal(true)}
                >
                    <i className="bi bi-arrow-left-right me-2"></i>โอนย้ายสต็อก
                </button>

                <select
                    className="form-select"
                    style={{ width: '200px' }}
                    value={selectedWarehouseId}
                    onChange={(e) => setSelectedWarehouseId(e.target.value)}
                >
                    {warehouses.map(w => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                </select>

                {activeTab === 'outbound' && (
                    <button className="btn btn-success" onClick={handleExport} disabled={!outboundData}>
                        <i className="bi bi-file-earmark-excel me-2"></i>Export CSV
                    </button>
                )}
                <button className="btn btn-primary" onClick={() => {
                    if (activeTab === 'summary') fetchSummary();
                    else if (activeTab === 'movements') fetchMovements();
                    else fetchOutbound();
                }}>
                    <i className={`bi bi-arrow-clockwise me-2 ${loading ? 'spin' : ''}`}></i>Refresh
                </button>
            </div>
        }>
            {/* Summary Cards */}
            {activeTab === 'summary' && (
                <>
                    {/* Date Info Banner */}
                    <div className="alert alert-info d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <i className="bi bi-info-circle me-2"></i>
                            <strong>สต็อกคงเหลือ ณ ปัจจุบัน</strong>
                            <span className="ms-2 text-muted">(คำนวณจาก Stock Ledger ทั้งหมด)</span>
                        </div>
                        <div className="text-muted small">
                            อัพเดทล่าสุด: {new Date().toLocaleString('th-TH')}
                        </div>
                    </div>

                    <div className="row g-3 mb-4">
                        <div className="col-md-4">
                            <div className="card bg-primary text-white h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">สต็อกทั้งหมด</h6>
                                    <h2 className="display-5 fw-bold mb-0">{totalOnHand.toLocaleString()}</h2>
                                    <div className="small opacity-75">ชิ้น</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="card bg-warning text-dark h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">จองแล้ว</h6>
                                    <h2 className="display-5 fw-bold mb-0">{totalAllocated.toLocaleString()}</h2>
                                    <div className="small opacity-75">ชิ้น</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="card bg-danger text-white h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">ใกล้หมด (&lt;10)</h6>
                                    <h2 className="display-5 fw-bold mb-0">{lowStockCount}</h2>
                                    <div className="small opacity-75">รายการ</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Warning if negative stock */}
                    {totalOnHand < 0 && (
                        <div className="alert alert-danger mb-3 d-flex justify-content-between align-items-center">
                            <div>
                                <i className="bi bi-exclamation-triangle me-2"></i>
                                <strong>⚠️ สต็อกติดลบ!</strong> มีสินค้าบางรายการสต็อกติดลบ อาจเกิดจากยังไม่ได้ตั้ง stock เริ่มต้น
                            </div>
                            <button
                                className="btn btn-warning btn-sm"
                                onClick={async () => {
                                    if (!confirm('ต้องการ Reset สต็อกที่ติดลบเป็น 0 หรือไม่? (จะเพิ่ม stock adjustment ให้ทุกรายการที่ติดลบ)')) return;
                                    try {
                                        const res = await api.post('/stock/reset-to-zero');
                                        alert(`สำเร็จ! แก้ไข ${res.data.fixed_products} รายการ, รวม ${res.data.total_adjusted} ชิ้น`);
                                        fetchSummary();
                                    } catch (e) {
                                        alert('เกิดข้อผิดพลาด: ' + (e as any).message);
                                    }
                                }}
                            >
                                🔧 Reset สต็อกติดลบเป็น 0
                            </button>
                        </div>
                    )}
                </>
            )}

            {/* Daily Outbound Cards */}
            {activeTab === 'outbound' && outboundData && (
                <>
                    {/* Date Picker */}
                    <div className="card border-0 shadow-sm mb-4">
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
                                    <label className="form-label">โหมดการนับ</label>
                                    <select
                                        className="form-select"
                                        value={dateMode}
                                        onChange={(e) => setDateMode(e.target.value as 'collection' | 'rts')}
                                    >
                                        <option value="collection">Courier รับแล้ว</option>
                                        <option value="rts">แพ็คแล้ว (RTS)</option>
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label">&nbsp;</label>
                                    <button className="btn btn-primary w-100 d-block" onClick={fetchOutbound} disabled={loading}>
                                        <i className={`bi ${loading ? 'bi-arrow-repeat spin' : 'bi-search'} me-2`}></i>
                                        โหลดข้อมูล
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Platform Breakdown */}
                    <div className="row g-3 mb-4">
                        <div className="col-md-4">
                            <div className="card h-100" style={{ backgroundColor: '#EE4D2D', color: 'white' }}>
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">Shopee</h6>
                                    <h3 className="fw-bold mb-0">{getPlatformStat('shopee').items.toLocaleString()} ชิ้น</h3>
                                    <div className="small opacity-75">{getPlatformStat('shopee').orders.toLocaleString()} ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="card bg-dark text-white h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">TikTok Shop</h6>
                                    <h3 className="fw-bold mb-0">{getPlatformStat('tiktok').items.toLocaleString()} ชิ้น</h3>
                                    <div className="small opacity-75">{getPlatformStat('tiktok').orders.toLocaleString()} ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-4">
                            <div className="card text-white h-100" style={{ backgroundColor: '#0f146d' }}>
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">Lazada</h6>
                                    <h3 className="fw-bold mb-0">{getPlatformStat('lazada').items.toLocaleString()} ชิ้น</h3>
                                    <div className="small opacity-75">{getPlatformStat('lazada').orders.toLocaleString()} ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Total Summary */}
                    <div className="row g-3 mb-4">
                        <div className="col-md-6">
                            <div className="card bg-success text-white h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">จำนวนสินค้าทั้งหมด</h6>
                                    <h2 className="display-4 fw-bold">{outboundData.total_items.toLocaleString()}</h2>
                                    <div className="small opacity-75">ชิ้น</div>
                                </div>
                            </div>
                        </div>
                        <div className="col-md-6">
                            <div className="card bg-info text-dark h-100">
                                <div className="card-body text-center">
                                    <h6 className="card-title opacity-75">จำนวนออเดอร์</h6>
                                    <h2 className="display-4 fw-bold">{outboundData.total_orders.toLocaleString()}</h2>
                                    <div className="small opacity-75">ออเดอร์</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* Tabs */}
            <ul className="nav nav-tabs mb-4">
                <li className="nav-item">
                    <button className={`nav-link ${activeTab === 'summary' ? 'active' : ''}`} onClick={() => setActiveTab('summary')}>
                        <i className="bi bi-box-seam me-2"></i>Stock Summary
                    </button>
                </li>
                <li className="nav-item">
                    <button className={`nav-link ${activeTab === 'outbound' ? 'active' : ''}`} onClick={() => setActiveTab('outbound')}>
                        <i className="bi bi-truck me-2"></i>Daily Outbound
                    </button>
                </li>
                <li className="nav-item">
                    <button className={`nav-link ${activeTab === 'movements' ? 'active' : ''}`} onClick={() => setActiveTab('movements')}>
                        <i className="bi bi-arrow-left-right me-2"></i>Movements
                    </button>
                </li>
            </ul>

            {/* Search (for summary tab) */}
            {activeTab === 'summary' && (
                <div className="mb-3">
                    <input
                        type="text"
                        className="form-control"
                        placeholder="ค้นหา SKU หรือ ชื่อสินค้า..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            )}

            {/* Table Content */}
            <div className="card shadow-sm border-0">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        {activeTab === 'summary' && (
                            <table className="table table-hover align-middle mb-0">
                                <thead className="bg-light">
                                    <tr>
                                        <th className="ps-4">SKU</th>
                                        <th>Name</th>
                                        <th className="text-end">On Hand</th>
                                        <th className="text-end">Allocated</th>
                                        <th className="text-end">Available</th>
                                        <th className="text-end pe-4">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredSummary.map((item, idx) => (
                                        <tr key={idx}>
                                            <td className="ps-4 fw-bold text-primary">{item.sku}</td>
                                            <td>{item.product_name}</td>
                                            <td className="text-end">{item.on_hand}</td>
                                            <td className="text-end text-warning">{item.allocated}</td>
                                            <td className={`text-end fw-bold ${(item.available || 0) < 10 ? 'text-danger' : 'text-success'}`}>
                                                {item.available}
                                            </td>
                                            <td className="text-end pe-4">
                                                <a
                                                    href={`/stock/card/${encodeURIComponent(item.sku)}`}
                                                    className="btn btn-sm btn-outline-primary"
                                                    title="ดู Stock Card"
                                                >
                                                    <i className="bi bi-card-list"></i>
                                                </a>
                                            </td>
                                        </tr>
                                    ))}
                                    {filteredSummary.length === 0 && !loading && <tr><td colSpan={6} className="text-center py-4">No stock data</td></tr>}
                                </tbody>
                            </table>
                        )}

                        {activeTab === 'outbound' && outboundData && (
                            <table className="table table-hover align-middle mb-0">
                                <thead className="table-light">
                                    <tr>
                                        <th className="ps-4">SKU</th>
                                        <th>ชื่อสินค้า</th>
                                        <th className="text-center">จำนวนที่ส่ง (ชิ้น)</th>
                                        <th className="text-center pe-4">จำนวนออเดอร์</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {outboundData.items.length === 0 ? (
                                        <tr>
                                            <td colSpan={4} className="text-center py-5 text-muted">
                                                ไม่พบข้อมูลการจัดส่งในวันนี้
                                            </td>
                                        </tr>
                                    ) : (
                                        outboundData.items.map((item, idx) => (
                                            <tr key={idx}>
                                                <td className="ps-4 fw-mono fw-semibold text-primary">{item.sku}</td>
                                                <td>{item.product_name}</td>
                                                <td className="text-center fw-bold fs-5">{(item.total_quantity || 0).toLocaleString()}</td>
                                                <td className="text-center text-muted pe-4">{item.order_count.toLocaleString()}</td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        )}

                        {activeTab === 'movements' && (
                            <>
                                {/* Date Filter for Movements */}
                                <div className="p-3 bg-light border-bottom">
                                    <div className="row g-2 align-items-end">
                                        <div className="col-auto">
                                            <label className="form-label small mb-1">จากวันที่</label>
                                            <input
                                                type="date"
                                                className="form-control form-control-sm"
                                                value={movementsStartDate}
                                                onChange={(e) => setMovementsStartDate(e.target.value)}
                                            />
                                        </div>
                                        <div className="col-auto">
                                            <label className="form-label small mb-1">ถึงวันที่</label>
                                            <input
                                                type="date"
                                                className="form-control form-control-sm"
                                                value={movementsEndDate}
                                                onChange={(e) => setMovementsEndDate(e.target.value)}
                                            />
                                        </div>
                                        <div className="col-auto">
                                            <button className="btn btn-primary btn-sm" onClick={fetchMovements} disabled={loading}>
                                                <i className={`bi ${loading ? 'bi-arrow-repeat spin' : 'bi-search'} me-1`}></i>
                                                โหลดข้อมูล
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <table className="table table-hover align-middle mb-0">
                                    <thead className="bg-light">
                                        <tr>
                                            <th className="ps-4">Date</th>
                                            <th>Type</th>
                                            <th>SKU</th>
                                            <th className="text-end pe-4">Qty</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {movements.map((m) => (
                                            <tr key={m.id}>
                                                <td className="ps-4">{new Date(m.created_at).toLocaleString()}</td>
                                                <td><span className={`badge bg-${m.movement_type === 'IN' ? 'success' : 'danger'}`}>{m.movement_type}</span></td>
                                                <td>{m.sku}</td>
                                                <td className="text-end pe-4 font-monospace">{m.quantity > 0 ? '+' : ''}{m.quantity}</td>
                                            </tr>
                                        ))}
                                        {movements.length === 0 && !loading && <tr><td colSpan={4} className="text-center py-4">ไม่พบ movements ในช่วงเวลานี้</td></tr>}
                                    </tbody>
                                </table>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Transfer Modal */}
            {showTransferModal && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">โอนย้ายสินค้าข้ามคลัง</h5>
                                <button type="button" className="btn-close" onClick={() => setShowTransferModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="mb-3">
                                    <label className="form-label">SKU สินค้า</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={transferForm.sku}
                                        onChange={e => setTransferForm({ ...transferForm, sku: e.target.value })}
                                        list="sku-options"
                                        placeholder="พิมพ์ SKU..."
                                    />
                                    <datalist id="sku-options">
                                        {summary.map(s => <option key={s.product_id} value={s.sku}>{s.product_name}</option>)}
                                    </datalist>
                                </div>
                                <div className="row g-3 mb-3">
                                    <div className="col-6">
                                        <label className="form-label">จากคลัง</label>
                                        <select
                                            className="form-select"
                                            value={transferForm.from_warehouse_id}
                                            onChange={e => setTransferForm({ ...transferForm, from_warehouse_id: e.target.value })}
                                        >
                                            <option value="">เลือกคลังต้นทาง</option>
                                            {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                                        </select>
                                    </div>
                                    <div className="col-6">
                                        <label className="form-label">ไปยังคลัง</label>
                                        <select
                                            className="form-select"
                                            value={transferForm.to_warehouse_id}
                                            onChange={e => setTransferForm({ ...transferForm, to_warehouse_id: e.target.value })}
                                        >
                                            <option value="">เลือกคลังปลายทาง</option>
                                            {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                                        </select>
                                    </div>
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">จำนวน</label>
                                    <input
                                        type="number"
                                        className="form-control"
                                        value={transferForm.quantity}
                                        onChange={e => setTransferForm({ ...transferForm, quantity: parseInt(e.target.value) || 0 })}
                                    />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowTransferModal(false)}>ยกเลิก</button>
                                <button type="button" className="btn btn-primary" onClick={handleTransfer}>ยืนยันการโอน</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Stock;
