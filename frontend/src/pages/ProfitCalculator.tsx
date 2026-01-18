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

    // Platform fee rates (estimated)
    const feeRates: Record<string, { commission: number; service: number; shipping: number }> = {
        'shopee': { commission: 4.0, service: 2.0, shipping: 6.0 },
        'tiktok': { commission: 3.0, service: 1.5, shipping: 3.0 },
        'lazada': { commission: 5.0, service: 2.0, shipping: 5.0 },
        'manual': { commission: 0, service: 0, shipping: 0 }
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

        items.forEach(item => {
            if (item.product) {
                totalRevenue += item.selling_price * item.quantity;
                totalCogs += (item.product.standard_cost || 0) * item.quantity;
            }
        });

        const commissionFee = totalRevenue * (rates.commission / 100);
        const serviceFee = totalRevenue * (rates.service / 100);
        const shippingFee = totalRevenue * (rates.shipping / 100);
        const totalFees = commissionFee + serviceFee + shippingFee;

        const netProfit = totalRevenue - totalCogs - totalFees;
        const margin = totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0;

        return {
            totalRevenue,
            totalCogs,
            commissionFee,
            serviceFee,
            shippingFee,
            totalFees,
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
                                <small className="text-muted d-block">ค่าธรรมเนียมโดยประมาณ:</small>
                                <div className="d-flex justify-content-between mt-1">
                                    <small>Commission: {feeRates[platform].commission}%</small>
                                    <small>Service: {feeRates[platform].service}%</small>
                                    <small>Shipping: {feeRates[platform].shipping}%</small>
                                </div>
                            </div>
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
                                    <tr className="text-muted">
                                        <td className="ps-4"><small>ค่า Commission ({feeRates[platform].commission}%)</small></td>
                                        <td className="text-end"><small>-฿{formatNumber(results.commissionFee)}</small></td>
                                    </tr>
                                    <tr className="text-muted">
                                        <td className="ps-4"><small>ค่าบริการ ({feeRates[platform].service}%)</small></td>
                                        <td className="text-end"><small>-฿{formatNumber(results.serviceFee)}</small></td>
                                    </tr>
                                    <tr className="text-muted">
                                        <td className="ps-4"><small>ค่าขนส่ง ({feeRates[platform].shipping}%)</small></td>
                                        <td className="text-end"><small>-฿{formatNumber(results.shippingFee)}</small></td>
                                    </tr>
                                    <tr>
                                        <td>รวมค่าธรรมเนียม</td>
                                        <td className="text-end text-danger">-฿{formatNumber(results.totalFees)}</td>
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
