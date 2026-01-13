import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/client';
import type { Product } from '../types';

interface OrderItemInput {
    product_id: string;
    sku: string;
    product_name: string;
    quantity: number;
    unit_price: number;
}

const OrderCreate: React.FC = () => {
    const navigate = useNavigate();
    const [items, setItems] = useState<OrderItemInput[]>([]);
    const [showProductModal, setShowProductModal] = useState(false);
    const [products, setProducts] = useState<Product[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(false);

    // Form state
    const [customerName, setCustomerName] = useState('');
    const [customerPhone, setCustomerPhone] = useState('');
    const [customerAddress, setCustomerAddress] = useState('');
    const [channelCode, setChannelCode] = useState('manual');
    const [paymentMethod, setPaymentMethod] = useState('TRANSFER');
    const [shippingMethod, setShippingMethod] = useState('KERRY');
    const [shippingFee, setShippingFee] = useState(0);
    const [discountAmount, setDiscountAmount] = useState(0);

    // Search products
    useEffect(() => {
        if (searchTerm.length > 0) {
            const timer = setTimeout(() => searchProducts(searchTerm), 300);
            return () => clearTimeout(timer);
        }
    }, [searchTerm]);

    const searchProducts = async (term: string) => {
        try {
            const { data } = await api.get(`/products?search=${encodeURIComponent(term)}`);
            setProducts(data.products || []);
        } catch (e) {
            console.error('Failed to search products:', e);
        }
    };

    const selectProduct = (product: Product) => {
        setItems([...items, {
            product_id: product.id,
            sku: product.sku,
            product_name: product.name,
            quantity: 1,
            unit_price: product.standard_price || 0
        }]);
        setShowProductModal(false);
        setSearchTerm('');
        setProducts([]);
    };

    const updateItemQuantity = (index: number, qty: number) => {
        const newItems = [...items];
        newItems[index].quantity = qty;
        setItems(newItems);
    };

    const updateItemPrice = (index: number, price: number) => {
        const newItems = [...items];
        newItems[index].unit_price = price;
        setItems(newItems);
    };

    const removeItem = (index: number) => {
        setItems(items.filter((_, i) => i !== index));
    };

    const subtotal = items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0);
    const totalAmount = subtotal + shippingFee - discountAmount;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (items.length === 0) {
            alert('กรุณาเพิ่มสินค้าอย่างน้อย 1 รายการ');
            return;
        }

        setLoading(true);
        try {
            const orderData = {
                channel_code: channelCode,
                customer_name: customerName,
                customer_phone: customerPhone,
                customer_address: customerAddress,
                payment_method: paymentMethod,
                shipping_method: shippingMethod,
                shipping_fee: shippingFee,
                discount_amount: discountAmount,
                items: items
            };

            const { data } = await api.post('/orders', orderData);
            navigate(`/orders/${data.id}`);
        } catch (e) {
            console.error('Failed to create order:', e);
            alert('เกิดข้อผิดพลาดในการสร้างออเดอร์');
        } finally {
            setLoading(false);
        }
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item"><a href="/orders" className="text-decoration-none">Orders</a></li>
            <li className="breadcrumb-item active">Create</li>
        </>
    );

    return (
        <Layout title="สร้างออเดอร์ใหม่" breadcrumb={breadcrumb}>
            <form onSubmit={handleSubmit}>
                <div className="row g-3">
                    {/* Customer Info */}
                    <div className="col-lg-8">
                        <div className="card mb-3 border-0 shadow-sm">
                            <div className="card-header bg-white">
                                <i className="bi bi-person me-2"></i>ข้อมูลลูกค้า
                            </div>
                            <div className="card-body">
                                <div className="row g-3">
                                    <div className="col-md-6">
                                        <label className="form-label">ชื่อลูกค้า *</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={customerName}
                                            onChange={(e) => setCustomerName(e.target.value)}
                                            required
                                        />
                                    </div>
                                    <div className="col-md-6">
                                        <label className="form-label">เบอร์โทร</label>
                                        <input
                                            type="tel"
                                            className="form-control"
                                            value={customerPhone}
                                            onChange={(e) => setCustomerPhone(e.target.value)}
                                        />
                                    </div>
                                    <div className="col-12">
                                        <label className="form-label">ที่อยู่จัดส่ง</label>
                                        <textarea
                                            className="form-control"
                                            rows={2}
                                            value={customerAddress}
                                            onChange={(e) => setCustomerAddress(e.target.value)}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Order Items */}
                        <div className="card mb-3 border-0 shadow-sm">
                            <div className="card-header bg-white d-flex justify-content-between align-items-center">
                                <span><i className="bi bi-cart me-2"></i>รายการสินค้า</span>
                                <button
                                    type="button"
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => setShowProductModal(true)}
                                >
                                    <i className="bi bi-plus"></i> เพิ่มรายการ
                                </button>
                            </div>
                            <div className="card-body p-0">
                                <table className="table mb-0">
                                    <thead className="bg-light">
                                        <tr>
                                            <th style={{ width: '40%' }}>สินค้า</th>
                                            <th style={{ width: '15%' }}>จำนวน</th>
                                            <th style={{ width: '20%' }}>ราคา/หน่วย</th>
                                            <th style={{ width: '20%' }}>รวม</th>
                                            <th style={{ width: '5%' }}></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items.length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="text-center text-muted py-4">
                                                    <i className="bi bi-bag-plus fs-1 d-block mb-2"></i>
                                                    คลิก "เพิ่มรายการ" เพื่อเพิ่มสินค้า
                                                </td>
                                            </tr>
                                        ) : (
                                            items.map((item, i) => (
                                                <tr key={i}>
                                                    <td>
                                                        <div className="fw-semibold">{item.sku}</div>
                                                        <small className="text-muted">{item.product_name}</small>
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-control form-control-sm"
                                                            value={item.quantity}
                                                            min={1}
                                                            onChange={(e) => updateItemQuantity(i, parseInt(e.target.value) || 1)}
                                                        />
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-control form-control-sm"
                                                            value={item.unit_price}
                                                            step="0.01"
                                                            onChange={(e) => updateItemPrice(i, parseFloat(e.target.value) || 0)}
                                                        />
                                                    </td>
                                                    <td className="fw-bold">
                                                        ฿{(item.quantity * item.unit_price).toLocaleString()}
                                                    </td>
                                                    <td>
                                                        <button
                                                            type="button"
                                                            className="btn btn-sm btn-outline-danger"
                                                            onClick={() => removeItem(i)}
                                                        >
                                                            <i className="bi bi-trash"></i>
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    {/* Order Summary */}
                    <div className="col-lg-4">
                        <div className="card mb-3 border-0 shadow-sm">
                            <div className="card-header bg-white">
                                <i className="bi bi-info-circle me-2"></i>รายละเอียดออเดอร์
                            </div>
                            <div className="card-body">
                                <div className="mb-3">
                                    <label className="form-label">ช่องทาง</label>
                                    <select
                                        className="form-select"
                                        value={channelCode}
                                        onChange={(e) => setChannelCode(e.target.value)}
                                    >
                                        <option value="manual">Manual / Key-in</option>
                                        <option value="facebook">Facebook</option>
                                        <option value="line">Line</option>
                                    </select>
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">วิธีชำระเงิน</label>
                                    <select
                                        className="form-select"
                                        value={paymentMethod}
                                        onChange={(e) => setPaymentMethod(e.target.value)}
                                    >
                                        <option value="TRANSFER">โอนเงิน</option>
                                        <option value="COD">เก็บเงินปลายทาง</option>
                                        <option value="CREDIT_CARD">บัตรเครดิต</option>
                                    </select>
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">วิธีจัดส่ง</label>
                                    <select
                                        className="form-select"
                                        value={shippingMethod}
                                        onChange={(e) => setShippingMethod(e.target.value)}
                                    >
                                        <option value="KERRY">Kerry Express</option>
                                        <option value="FLASH">Flash Express</option>
                                        <option value="THAIPOST">ไปรษณีย์ไทย</option>
                                        <option value="PICKUP">รับเอง</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div className="card border-0 shadow-sm">
                            <div className="card-header bg-white">
                                <i className="bi bi-calculator me-2"></i>สรุปยอด
                            </div>
                            <div className="card-body">
                                <div className="d-flex justify-content-between mb-2">
                                    <span className="text-muted">ราคารวม</span>
                                    <span className="fw-bold">฿{subtotal.toLocaleString()}</span>
                                </div>
                                <div className="d-flex justify-content-between mb-2 align-items-center">
                                    <span className="text-muted">ค่าจัดส่ง</span>
                                    <input
                                        type="number"
                                        className="form-control form-control-sm text-end"
                                        style={{ width: '100px' }}
                                        value={shippingFee}
                                        onChange={(e) => setShippingFee(parseFloat(e.target.value) || 0)}
                                    />
                                </div>
                                <div className="d-flex justify-content-between mb-3 align-items-center">
                                    <span className="text-muted">ส่วนลด</span>
                                    <input
                                        type="number"
                                        className="form-control form-control-sm text-end"
                                        style={{ width: '100px' }}
                                        value={discountAmount}
                                        onChange={(e) => setDiscountAmount(parseFloat(e.target.value) || 0)}
                                    />
                                </div>
                                <hr />
                                <div className="d-flex justify-content-between fs-5 fw-bold">
                                    <span>ยอดรวมสุทธิ</span>
                                    <span className="text-primary">฿{totalAmount.toLocaleString()}</span>
                                </div>
                            </div>
                            <div className="card-footer bg-white">
                                <button
                                    type="submit"
                                    className="btn btn-primary w-100"
                                    disabled={loading}
                                >
                                    {loading ? (
                                        <><span className="spinner-border spinner-border-sm me-1"></span> กำลังสร้าง...</>
                                    ) : (
                                        <><i className="bi bi-check-circle me-1"></i> สร้างออเดอร์</>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </form>

            {/* Product Search Modal */}
            {showProductModal && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-lg">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">เลือกสินค้า</h5>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={() => {
                                        setShowProductModal(false);
                                        setSearchTerm('');
                                        setProducts([]);
                                    }}
                                />
                            </div>
                            <div className="modal-body">
                                <div className="input-group mb-3">
                                    <span className="input-group-text"><i className="bi bi-search"></i></span>
                                    <input
                                        type="text"
                                        className="form-control"
                                        placeholder="ค้นหา SKU หรือชื่อสินค้า..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        autoFocus
                                    />
                                </div>
                                <div className="table-responsive" style={{ maxHeight: '400px' }}>
                                    <table className="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>SKU</th>
                                                <th>ชื่อสินค้า</th>
                                                <th>ราคา</th>
                                                <th></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {products.length === 0 ? (
                                                <tr>
                                                    <td colSpan={4} className="text-center text-muted">
                                                        {searchTerm ? 'ไม่พบสินค้า' : 'กรุณาค้นหาสินค้า'}
                                                    </td>
                                                </tr>
                                            ) : (
                                                products.map(p => (
                                                    <tr
                                                        key={p.id}
                                                        className="cursor-pointer"
                                                        onClick={() => selectProduct(p)}
                                                        style={{ cursor: 'pointer' }}
                                                    >
                                                        <td className="fw-mono">{p.sku}</td>
                                                        <td>{p.name}</td>
                                                        <td>฿{p.standard_price || 0}</td>
                                                        <td>
                                                            <button className="btn btn-sm btn-primary">
                                                                <i className="bi bi-plus"></i>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
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

export default OrderCreate;
