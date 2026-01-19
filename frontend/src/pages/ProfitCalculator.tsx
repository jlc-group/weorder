import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface Product {
    id: string;
    sku: string;
    name: string;
    standard_cost: number;
    retail_price: number;
}

interface CalculatorItem {
    product: Product | null;
    selling_price: number;
    quantity: number;
}

const ProfitCalculator: React.FC = () => {
    const [products, setProducts] = useState<Product[]>([]);
    const [items, setItems] = useState<CalculatorItem[]>([
        { product: null, selling_price: 0, quantity: 1 }
    ]);
    const [platform, setPlatform] = useState('shopee');
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(true);
    const [showFeeEditor, setShowFeeEditor] = useState(false);
    const [showExtraCosts, setShowExtraCosts] = useState(false);

    // Additional costs (per order)
    const [extraCosts, setExtraCosts] = useState({
        ads: 0,           // ค่าโฆษณา (บาท/ออเดอร์)
        adsPercent: 5,    // ค่าโฆษณา (% ของยอดขาย)
        adsMode: 'percent' as 'fixed' | 'percent',
        packaging: 15,    // ค่ากล่อง/บรรจุภัณฑ์
        labor: 5,         // ค่าแรงแพ็ค
        vatPercent: 0,    // VAT (ถ้ามี)
        other: 0          // ค่าใช้จ่ายอื่นๆ
    });

    // Platform fee rates (editable)
    const defaultFeeRates: Record<string, { commission: number; service: number; shipping: number }> = {
        'shopee': { commission: 4.0, service: 2.0, shipping: 6.0 },
        'tiktok': { commission: 3.0, service: 1.5, shipping: 3.0 },
        'lazada': { commission: 5.0, service: 2.0, shipping: 5.0 },
        'manual': { commission: 0, service: 0, shipping: 0 }
    };
    const [feeRates, setFeeRates] = useState(defaultFeeRates);

    const updateFeeRate = (platform: string, field: 'commission' | 'service' | 'shipping', value: number) => {
        setFeeRates(prev => ({
            ...prev,
            [platform]: {
                ...prev[platform],
                [field]: value
            }
        }));
    };

    useEffect(() => {
        const fetchProducts = async () => {
            try {
                const res = await api.get('/products?per_page=500');
                setProducts(res.data.products || []);
            } catch (error) {
                console.error("Error fetching products:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchProducts();
    }, []);

    const addItem = () => {
        setItems([...items, { product: null, selling_price: 0, quantity: 1 }]);
    };

    const removeItem = (index: number) => {
        if (items.length > 1) {
            setItems(items.filter((_, i) => i !== index));
        }
    };

    const updateItem = (index: number, field: keyof CalculatorItem, value: any) => {
        const newItems = [...items];
        if (field === 'product') {
            newItems[index].product = value;
            newItems[index].selling_price = value?.retail_price || 0;
        } else {
            (newItems[index] as any)[field] = value;
        }
        setItems(newItems);
    };

    // Calculate totals
    const calculateResults = () => {
        const rates = feeRates[platform];
        let totalRevenue = 0;
        let totalCogs = 0;
        let totalQuantity = 0;

        items.forEach(item => {
            if (item.product) {
                const revenue = item.selling_price * item.quantity;
                totalRevenue += revenue;
                totalQuantity += item.quantity;
                // ถ้าไม่มี standard_cost ให้ใช้ 30% ของราคาขายเป็นต้นทุน
                const cost = item.product.standard_cost > 0
                    ? item.product.standard_cost
                    : item.selling_price * 0.30;
                totalCogs += cost * item.quantity;
            }
        });

        // Platform fees
        const commissionFee = totalRevenue * (rates.commission / 100);
        const serviceFee = totalRevenue * (rates.service / 100);
        const shippingFee = totalRevenue * (rates.shipping / 100);
        const totalPlatformFees = commissionFee + serviceFee + shippingFee;

        // Additional costs
        const adsCost = extraCosts.adsMode === 'percent'
            ? totalRevenue * (extraCosts.adsPercent / 100)
            : extraCosts.ads;
        const packagingCost = extraCosts.packaging; // per order
        const laborCost = extraCosts.labor; // per order
        const vatCost = totalRevenue * (extraCosts.vatPercent / 100);
        const otherCost = extraCosts.other;
        const totalExtraCosts = adsCost + packagingCost + laborCost + vatCost + otherCost;

        const totalAllCosts = totalPlatformFees + totalExtraCosts;
        const netProfit = totalRevenue - totalCogs - totalAllCosts;
        const margin = totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0;

        return {
            totalRevenue,
            totalCogs,
            totalQuantity,
            commissionFee,
            serviceFee,
            shippingFee,
            totalPlatformFees,
            adsCost,
            packagingCost,
            laborCost,
            vatCost,
            otherCost,
            totalExtraCosts,
            totalAllCosts,
            netProfit,
            margin
        };
    };

    const results = calculateResults();

    const formatNumber = (num: number) => {
        return num.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const filteredProducts = products.filter(p =>
        p.sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.name?.toLowerCase().includes(searchTerm.toLowerCase())
    ).slice(0, 20);

    const breadcrumb = (
        <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
                <li className="breadcrumb-item"><a href="/finance">การเงิน</a></li>
                <li className="breadcrumb-item active">คำนวณกำไร</li>
            </ol>
        </nav>
    );

    return (
        <Layout title="🧮 คำนวณกำไร" breadcrumb={breadcrumb}>
            <div className="row g-4">
                {/* Left: Product Selection */}
                <div className="col-lg-7">
                    <div className="card border-0 shadow-sm">
                        <div className="card-header bg-white py-3 d-flex justify-content-between align-items-center">
                            <h5 className="mb-0">
                                <i className="bi bi-box me-2"></i>เลือกสินค้า
                            </h5>
                            <button className="btn btn-sm btn-success" onClick={addItem}>
                                <i className="bi bi-plus-lg me-1"></i>เพิ่มสินค้า
                            </button>
                        </div>
                        <div className="card-body">
                            {loading ? (
                                <div className="text-center py-4">
                                    <div className="spinner-border text-primary"></div>
                                </div>
                            ) : (
                                <div className="table-responsive">
                                    <table className="table align-middle">
                                        <thead>
                                            <tr>
                                                <th style={{ width: '40%' }}>สินค้า</th>
                                                <th style={{ width: '25%' }}>ราคาขาย</th>
                                                <th style={{ width: '20%' }}>จำนวน</th>
                                                <th style={{ width: '15%' }}>ต้นทุน</th>
                                                <th></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {items.map((item, idx) => (
                                                <tr key={idx}>
                                                    <td>
                                                        <input
                                                            type="text"
                                                            className="form-control form-control-sm"
                                                            placeholder="ค้นหา SKU หรือชื่อ..."
                                                            list={`products-${idx}`}
                                                            value={item.product?.sku || searchTerm}
                                                            onChange={(e) => {
                                                                setSearchTerm(e.target.value);
                                                                const found = products.find(p => p.sku === e.target.value);
                                                                if (found) {
                                                                    updateItem(idx, 'product', found);
                                                                }
                                                            }}
                                                        />
                                                        <datalist id={`products-${idx}`}>
                                                            {filteredProducts.map(p => (
                                                                <option key={p.id} value={p.sku}>
                                                                    {p.name} (฿{p.standard_cost})
                                                                </option>
                                                            ))}
                                                        </datalist>
                                                        {item.product && (
                                                            <small className="text-muted d-block mt-1">
                                                                {item.product.name?.substring(0, 40)}...
                                                            </small>
                                                        )}
                                                    </td>
                                                    <td>
                                                        <div className="input-group input-group-sm">
                                                            <span className="input-group-text">฿</span>
                                                            <input
                                                                type="number"
                                                                className="form-control"
                                                                value={item.selling_price}
                                                                onChange={(e) => updateItem(idx, 'selling_price', parseFloat(e.target.value) || 0)}
                                                            />
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-control form-control-sm"
                                                            min="1"
                                                            value={item.quantity}
                                                            onChange={(e) => updateItem(idx, 'quantity', parseInt(e.target.value) || 1)}
                                                        />
                                                    </td>
                                                    <td className="text-warning fw-bold">
                                                        ฿{formatNumber(item.product?.standard_cost || 0)}
                                                    </td>
                                                    <td>
                                                        <button
                                                            className="btn btn-sm btn-outline-danger"
                                                            onClick={() => removeItem(idx)}
                                                            disabled={items.length <= 1}
                                                        >
                                                            <i className="bi bi-trash"></i>
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: Results */}
                <div className="col-lg-5">
                    {/* Platform Selection */}
                    <div className="card border-0 shadow-sm mb-4">
                        <div className="card-body">
                            <h6 className="mb-3"><i className="bi bi-shop me-2"></i>Platform</h6>
                            <div className="btn-group w-100" role="group">
                                {Object.keys(feeRates).map(p => (
                                    <button
                                        key={p}
                                        className={`btn ${platform === p ? 'btn-primary' : 'btn-outline-primary'}`}
                                        onClick={() => setPlatform(p)}
                                    >
                                        {p === 'shopee' && '🟠'}
                                        {p === 'tiktok' && '⚫'}
                                        {p === 'lazada' && '🔵'}
                                        {p === 'manual' && '📝'}
                                        {' '}{p.charAt(0).toUpperCase() + p.slice(1)}
                                    </button>
                                ))}
                            </div>
                            <div className="mt-3 p-3 bg-light rounded">
                                <div className="d-flex justify-content-between align-items-center mb-2">
                                    <small className="text-muted">ค่าธรรมเนียม:</small>
                                    <button
                                        className="btn btn-sm btn-link p-0"
                                        onClick={() => setShowFeeEditor(!showFeeEditor)}
                                    >
                                        <i className={`bi ${showFeeEditor ? 'bi-chevron-up' : 'bi-pencil'}`}></i>
                                        {showFeeEditor ? ' ซ่อน' : ' แก้ไข'}
                                    </button>
                                </div>
                                {showFeeEditor ? (
                                    <div className="row g-2">
                                        <div className="col-4">
                                            <label className="form-label small mb-1">Commission %</label>
                                            <input
                                                type="number"
                                                className="form-control form-control-sm"
                                                value={feeRates[platform].commission}
                                                onChange={(e) => updateFeeRate(platform, 'commission', parseFloat(e.target.value) || 0)}
                                                step="0.5"
                                                min="0"
                                                max="100"
                                            />
                                        </div>
                                        <div className="col-4">
                                            <label className="form-label small mb-1">Service %</label>
                                            <input
                                                type="number"
                                                className="form-control form-control-sm"
                                                value={feeRates[platform].service}
                                                onChange={(e) => updateFeeRate(platform, 'service', parseFloat(e.target.value) || 0)}
                                                step="0.5"
                                                min="0"
                                                max="100"
                                            />
                                        </div>
                                        <div className="col-4">
                                            <label className="form-label small mb-1">Shipping %</label>
                                            <input
                                                type="number"
                                                className="form-control form-control-sm"
                                                value={feeRates[platform].shipping}
                                                onChange={(e) => updateFeeRate(platform, 'shipping', parseFloat(e.target.value) || 0)}
                                                step="0.5"
                                                min="0"
                                                max="100"
                                            />
                                        </div>
                                        <div className="col-12 mt-2">
                                            <small className="text-muted">
                                                รวม: {(feeRates[platform].commission + feeRates[platform].service + feeRates[platform].shipping).toFixed(1)}%
                                            </small>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="d-flex justify-content-between mt-1">
                                        <small>Commission: {feeRates[platform].commission}%</small>
                                        <small>Service: {feeRates[platform].service}%</small>
                                        <small>Shipping: {feeRates[platform].shipping}%</small>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Extra Costs */}
                    <div className="card border-0 shadow-sm mb-4">
                        <div className="card-body">
                            <div className="d-flex justify-content-between align-items-center mb-3">
                                <h6 className="mb-0"><i className="bi bi-receipt me-2"></i>ค่าใช้จ่ายเพิ่มเติม</h6>
                                <button
                                    className="btn btn-sm btn-link p-0"
                                    onClick={() => setShowExtraCosts(!showExtraCosts)}
                                >
                                    <i className={`bi ${showExtraCosts ? 'bi-chevron-up' : 'bi-pencil'}`}></i>
                                    {showExtraCosts ? ' ซ่อน' : ' แก้ไข'}
                                </button>
                            </div>
                            {showExtraCosts ? (
                                <div className="row g-2">
                                    <div className="col-12">
                                        <label className="form-label small mb-1">📢 ค่าโฆษณา (Ads)</label>
                                        <div className="input-group input-group-sm">
                                            <button
                                                className={`btn ${extraCosts.adsMode === 'percent' ? 'btn-primary' : 'btn-outline-secondary'}`}
                                                onClick={() => setExtraCosts(prev => ({ ...prev, adsMode: 'percent' }))}
                                            >%</button>
                                            <button
                                                className={`btn ${extraCosts.adsMode === 'fixed' ? 'btn-primary' : 'btn-outline-secondary'}`}
                                                onClick={() => setExtraCosts(prev => ({ ...prev, adsMode: 'fixed' }))}
                                            >฿</button>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={extraCosts.adsMode === 'percent' ? extraCosts.adsPercent : extraCosts.ads}
                                                onChange={(e) => setExtraCosts(prev => ({
                                                    ...prev,
                                                    [extraCosts.adsMode === 'percent' ? 'adsPercent' : 'ads']: parseFloat(e.target.value) || 0
                                                }))}
                                                step="0.5"
                                                min="0"
                                            />
                                        </div>
                                    </div>
                                    <div className="col-6">
                                        <label className="form-label small mb-1">📦 ค่ากล่อง/แพ็ค</label>
                                        <div className="input-group input-group-sm">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={extraCosts.packaging}
                                                onChange={(e) => setExtraCosts(prev => ({ ...prev, packaging: parseFloat(e.target.value) || 0 }))}
                                                min="0"
                                            />
                                        </div>
                                    </div>
                                    <div className="col-6">
                                        <label className="form-label small mb-1">👷 ค่าแรงแพ็ค</label>
                                        <div className="input-group input-group-sm">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={extraCosts.labor}
                                                onChange={(e) => setExtraCosts(prev => ({ ...prev, labor: parseFloat(e.target.value) || 0 }))}
                                                min="0"
                                            />
                                        </div>
                                    </div>
                                    <div className="col-6">
                                        <label className="form-label small mb-1">🏛️ VAT %</label>
                                        <div className="input-group input-group-sm">
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={extraCosts.vatPercent}
                                                onChange={(e) => setExtraCosts(prev => ({ ...prev, vatPercent: parseFloat(e.target.value) || 0 }))}
                                                min="0"
                                                max="100"
                                            />
                                            <span className="input-group-text">%</span>
                                        </div>
                                    </div>
                                    <div className="col-6">
                                        <label className="form-label small mb-1">📋 อื่นๆ</label>
                                        <div className="input-group input-group-sm">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={extraCosts.other}
                                                onChange={(e) => setExtraCosts(prev => ({ ...prev, other: parseFloat(e.target.value) || 0 }))}
                                                min="0"
                                            />
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="d-flex flex-wrap gap-2">
                                    <span className="badge bg-light text-dark">
                                        📢 Ads: {extraCosts.adsMode === 'percent' ? `${extraCosts.adsPercent}%` : `฿${extraCosts.ads}`}
                                    </span>
                                    <span className="badge bg-light text-dark">📦 กล่อง: ฿{extraCosts.packaging}</span>
                                    <span className="badge bg-light text-dark">👷 แรง: ฿{extraCosts.labor}</span>
                                    {extraCosts.vatPercent > 0 && <span className="badge bg-light text-dark">🏛️ VAT: {extraCosts.vatPercent}%</span>}
                                    {extraCosts.other > 0 && <span className="badge bg-light text-dark">📋 อื่นๆ: ฿{extraCosts.other}</span>}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Calculation Results */}
                    <div className="card border-0 shadow-sm">
                        <div className="card-header bg-white py-3">
                            <h5 className="mb-0"><i className="bi bi-calculator me-2"></i>ผลการคำนวณ</h5>
                        </div>
                        <div className="card-body">
                            <table className="table table-sm">
                                <tbody>
                                    <tr>
                                        <td>ยอดขายรวม</td>
                                        <td className="text-end text-success fw-bold">฿{formatNumber(results.totalRevenue)}</td>
                                    </tr>
                                    <tr>
                                        <td>ต้นทุนสินค้า (COGS)</td>
                                        <td className="text-end text-warning">-฿{formatNumber(results.totalCogs)}</td>
                                    </tr>

                                    {/* Platform Fees */}
                                    <tr className="table-light">
                                        <td colSpan={2}><small className="fw-bold">ค่าธรรมเนียม Platform</small></td>
                                    </tr>
                                    <tr className="text-muted">
                                        <td className="ps-4"><small>Commission ({feeRates[platform].commission}%)</small></td>
                                        <td className="text-end"><small>-฿{formatNumber(results.commissionFee)}</small></td>
                                    </tr>
                                    <tr className="text-muted">
                                        <td className="ps-4"><small>Service ({feeRates[platform].service}%)</small></td>
                                        <td className="text-end"><small>-฿{formatNumber(results.serviceFee)}</small></td>
                                    </tr>
                                    <tr className="text-muted">
                                        <td className="ps-4"><small>Shipping ({feeRates[platform].shipping}%)</small></td>
                                        <td className="text-end"><small>-฿{formatNumber(results.shippingFee)}</small></td>
                                    </tr>
                                    <tr>
                                        <td className="ps-4 fw-bold">รวมค่า Platform</td>
                                        <td className="text-end text-danger">-฿{formatNumber(results.totalPlatformFees)}</td>
                                    </tr>

                                    {/* Extra Costs */}
                                    <tr className="table-light">
                                        <td colSpan={2}><small className="fw-bold">ค่าใช้จ่ายเพิ่มเติม</small></td>
                                    </tr>
                                    {results.adsCost > 0 && (
                                        <tr className="text-muted">
                                            <td className="ps-4"><small>📢 ค่าโฆษณา</small></td>
                                            <td className="text-end"><small>-฿{formatNumber(results.adsCost)}</small></td>
                                        </tr>
                                    )}
                                    {results.packagingCost > 0 && (
                                        <tr className="text-muted">
                                            <td className="ps-4"><small>📦 ค่ากล่อง/แพ็ค</small></td>
                                            <td className="text-end"><small>-฿{formatNumber(results.packagingCost)}</small></td>
                                        </tr>
                                    )}
                                    {results.laborCost > 0 && (
                                        <tr className="text-muted">
                                            <td className="ps-4"><small>👷 ค่าแรงแพ็ค</small></td>
                                            <td className="text-end"><small>-฿{formatNumber(results.laborCost)}</small></td>
                                        </tr>
                                    )}
                                    {results.vatCost > 0 && (
                                        <tr className="text-muted">
                                            <td className="ps-4"><small>🏛️ VAT ({extraCosts.vatPercent}%)</small></td>
                                            <td className="text-end"><small>-฿{formatNumber(results.vatCost)}</small></td>
                                        </tr>
                                    )}
                                    {results.otherCost > 0 && (
                                        <tr className="text-muted">
                                            <td className="ps-4"><small>📋 อื่นๆ</small></td>
                                            <td className="text-end"><small>-฿{formatNumber(results.otherCost)}</small></td>
                                        </tr>
                                    )}
                                    <tr>
                                        <td className="ps-4 fw-bold">รวมค่าใช้จ่ายเพิ่มเติม</td>
                                        <td className="text-end text-danger">-฿{formatNumber(results.totalExtraCosts)}</td>
                                    </tr>

                                    <tr className="table-secondary">
                                        <td><strong>รวมค่าใช้จ่ายทั้งหมด</strong></td>
                                        <td className="text-end text-danger fw-bold">-฿{formatNumber(results.totalAllCosts + results.totalCogs)}</td>
                                    </tr>
                                </tbody>
                            </table>

                            <hr />

                            <div className={`text-center p-4 rounded ${results.netProfit >= 0 ? 'bg-success' : 'bg-danger'} bg-opacity-10`}>
                                <h6 className="text-muted mb-1">กำไรสุทธิ</h6>
                                <h2 className={`fw-bold mb-1 ${results.netProfit >= 0 ? 'text-success' : 'text-danger'}`}>
                                    ฿{formatNumber(results.netProfit)}
                                </h2>
                                <span className={`badge ${results.margin >= 15 ? 'bg-success' : results.margin >= 0 ? 'bg-warning' : 'bg-danger'}`}>
                                    Margin: {results.margin.toFixed(1)}%
                                </span>
                            </div>

                            {results.margin < 15 && results.margin >= 0 && (
                                <div className="alert alert-warning mt-3 mb-0">
                                    <i className="bi bi-exclamation-triangle me-2"></i>
                                    <small>Margin ต่ำกว่า 15% - แนะนำเพิ่มราคาขาย</small>
                                </div>
                            )}
                            {results.netProfit < 0 && (
                                <div className="alert alert-danger mt-3 mb-0">
                                    <i className="bi bi-x-circle me-2"></i>
                                    <small>ขาดทุน! กรุณาปรับราคาขายใหม่</small>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default ProfitCalculator;
