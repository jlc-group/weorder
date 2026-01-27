import React, { useEffect, useState, useCallback } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';
import type { Product } from '../types';

const Products: React.FC = () => {
    // === State ===
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // === Filter State ===
    const [filterType, setFilterType] = useState<string>('all');
    const [search, setSearch] = useState('');
    const [stockFilter, setStockFilter] = useState<string>('all'); // all, low, out

    // === Bulk Selection ===
    const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set());

    // === Edit/Add Modal State ===
    const [editingProduct, setEditingProduct] = useState<Partial<Product> | null>(null);
    const [showEditModal, setShowEditModal] = useState<boolean>(false);
    const [editForm, setEditForm] = useState<Partial<Product>>({});

    const fetchProducts = useCallback(async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (filterType && filterType !== 'all') params.product_type = filterType;

            const response = await api.get('/products', { params });
            if (response.data && response.data.products) {
                setProducts(response.data.products);
            } else {
                setProducts([]);
            }
            setError(null);
        } catch (err) {
            console.error("Failed to fetch products:", err);
            setError("Failed to load products");
        } finally {
            setLoading(false);
        }
    }, [filterType]);

    useEffect(() => {
        fetchProducts();
    }, [fetchProducts]);

    // Filtered products (client-side search)
    const filteredProducts = React.useMemo(() => {
        let result = products;

        // Search filter
        if (search) {
            const s = search.toLowerCase();
            result = result.filter(p =>
                p.sku.toLowerCase().includes(s) ||
                p.name.toLowerCase().includes(s)
            );
        }

        // Stock filter (assuming stock_quantity exists or defaulting to 0)
        if (stockFilter === 'low') {
            result = result.filter(p => (p.stock_quantity ?? 0) > 0 && (p.stock_quantity ?? 0) <= 10);
        } else if (stockFilter === 'out') {
            result = result.filter(p => (p.stock_quantity ?? 0) === 0);
        }

        return result;
    }, [products, search, stockFilter]);

    // Summary stats
    const summary = React.useMemo(() => {
        const total = products.length;
        const active = products.filter(p => p.is_active).length;
        const inactive = products.filter(p => !p.is_active).length;
        const lowStock = products.filter(p => (p.stock_quantity ?? 0) > 0 && (p.stock_quantity ?? 0) <= 10).length;
        const outOfStock = products.filter(p => (p.stock_quantity ?? 0) === 0).length;
        return { total, active, inactive, lowStock, outOfStock };
    }, [products]);

    // === Handlers ===
    const openAddModal = () => {
        setEditingProduct({});
        setEditForm({ product_type: 'NORMAL', is_active: true });
        setShowEditModal(true);
    };

    const openEditModal = (product: Product) => {
        setEditingProduct(product);
        setEditForm({ ...product });
        setShowEditModal(true);
    };

    const handleSaveProduct = async () => {
        if (!editingProduct) return;
        try {
            let productId = editingProduct.id;

            if (productId) {
                await api.put(`/products/${productId}`, editForm);
            } else {
                if (!editForm.sku || !editForm.name) {
                    alert("กรุณากรอก SKU และชื่อสินค้า");
                    return;
                }
                await api.post('/products', editForm);
            }

            setShowEditModal(false);
            fetchProducts();
        } catch (err) {
            console.error("Failed to save product", err);
            alert("บันทึกไม่สำเร็จ: " + ((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || ""));
        }
    };

    // Bulk selection
    const toggleSelect = (id: string) => {
        const newSet = new Set(selectedProducts);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        setSelectedProducts(newSet);
    };

    const toggleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedProducts(new Set(filteredProducts.map(p => p.id)));
        } else {
            setSelectedProducts(new Set());
        }
    };

    // Bulk activate/deactivate
    const handleBulkActivate = async (active: boolean) => {
        if (selectedProducts.size === 0) return;
        try {
            for (const id of selectedProducts) {
                await api.put(`/products/${id}`, { is_active: active });
            }
            setSelectedProducts(new Set());
            fetchProducts();
        } catch (e) {
            console.error('Bulk update failed:', e);
            alert('เกิดข้อผิดพลาด');
        }
    };

    const breadcrumb = (
        <li className="breadcrumb-item active" aria-current="page">สินค้า</li>
    );

    const isEditing = !!editingProduct?.id;

    return (
        <Layout
            title="จัดการสินค้า"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <button className="btn btn-outline-primary" onClick={fetchProducts} disabled={loading}>
                        <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                    </button>
                    <button className="btn btn-primary" onClick={openAddModal}>
                        <i className="bi bi-plus-lg me-2"></i>เพิ่มสินค้า
                    </button>
                </div>
            }
        >
            {error && <div className="alert alert-danger">{error}</div>}

            {/* Summary Cards */}
            <div className="row g-3 mb-4">
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-3 fw-bold text-primary">{summary.total}</div>
                            <div className="text-muted small">สินค้าทั้งหมด</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-3 fw-bold text-success">{summary.active}</div>
                            <div className="text-muted small">เปิดขาย</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-2">
                    <div className="card border-0 shadow-sm h-100">
                        <div className="card-body text-center py-3">
                            <div className="fs-3 fw-bold text-secondary">{summary.inactive}</div>
                            <div className="text-muted small">ปิดขาย</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-3">
                    <div
                        className={`card border-0 shadow-sm h-100 cursor-pointer ${stockFilter === 'low' ? 'border-warning border-2' : ''}`}
                        onClick={() => setStockFilter(stockFilter === 'low' ? 'all' : 'low')}
                        style={{ cursor: 'pointer' }}
                    >
                        <div className="card-body text-center py-3">
                            <div className="fs-3 fw-bold text-warning">{summary.lowStock}</div>
                            <div className="text-muted small">สต๊อกต่ำ (≤10)</div>
                        </div>
                    </div>
                </div>
                <div className="col-md-3">
                    <div
                        className={`card border-0 shadow-sm h-100 cursor-pointer ${stockFilter === 'out' ? 'border-danger border-2' : ''}`}
                        onClick={() => setStockFilter(stockFilter === 'out' ? 'all' : 'out')}
                        style={{ cursor: 'pointer' }}
                    >
                        <div className="card-body text-center py-3">
                            <div className="fs-3 fw-bold text-danger">{summary.outOfStock}</div>
                            <div className="text-muted small">สินค้าหมด</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Filters */}
            <div className="card mb-3 border-0 shadow-sm">
                <div className="card-body py-3">
                    <div className="row g-2 align-items-center">
                        <div className="col-md-3">
                            <div className="input-group">
                                <span className="input-group-text"><i className="bi bi-search"></i></span>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="ค้นหา SKU หรือชื่อสินค้า..."
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="col-md-2">
                            <select
                                className="form-select"
                                value={filterType}
                                onChange={(e) => setFilterType(e.target.value)}
                            >
                                <option value="all">ทุกประเภท</option>
                                <option value="NORMAL">สินค้าปกติ</option>
                                <option value="SERVICE">บริการ</option>
                                <option value="SET">ชุดสินค้า</option>
                            </select>
                        </div>
                        <div className="col-md-2">
                            <select
                                className="form-select"
                                value={stockFilter}
                                onChange={(e) => setStockFilter(e.target.value)}
                            >
                                <option value="all">ทุกสถานะสต๊อก</option>
                                <option value="low">สต๊อกต่ำ (≤10)</option>
                                <option value="out">สินค้าหมด</option>
                            </select>
                        </div>
                        <div className="col-md-5 text-end">
                            <span className="text-muted">แสดง {filteredProducts.length} จาก {products.length} รายการ</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bulk Action Bar */}
            {selectedProducts.size > 0 && (
                <div className="alert alert-info d-flex justify-content-between align-items-center mb-3">
                    <span><strong>{selectedProducts.size}</strong> รายการถูกเลือก</span>
                    <div className="d-flex gap-2">
                        <button className="btn btn-sm btn-success" onClick={() => handleBulkActivate(true)}>
                            <i className="bi bi-check-circle me-1"></i>เปิดขาย
                        </button>
                        <button className="btn btn-sm btn-secondary" onClick={() => handleBulkActivate(false)}>
                            <i className="bi bi-x-circle me-1"></i>ปิดขาย
                        </button>
                        <button className="btn btn-sm btn-outline-secondary" onClick={() => setSelectedProducts(new Set())}>
                            ยกเลิกการเลือก
                        </button>
                    </div>
                </div>
            )}

            {/* Products Table */}
            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-3 py-3" style={{ width: '40px' }}>
                                        <input
                                            type="checkbox"
                                            className="form-check-input"
                                            checked={filteredProducts.length > 0 && selectedProducts.size === filteredProducts.length}
                                            onChange={(e) => toggleSelectAll(e.target.checked)}
                                        />
                                    </th>
                                    <th className="py-3" style={{ width: '60px' }}>รูป</th>
                                    <th className="py-3">รายละเอียด</th>
                                    <th className="py-3">ประเภท</th>
                                    <th className="py-3 text-end">ต้นทุน</th>
                                    <th className="py-3 text-end">ราคา</th>
                                    <th className="py-3 text-center">สต๊อก</th>
                                    <th className="py-3 text-center">สถานะ</th>
                                    <th className="pe-3 py-3 text-end" style={{ width: '100px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && products.length === 0 ? (
                                    <tr>
                                        <td colSpan={9} className="text-center py-5 text-muted">
                                            <div className="spinner-border text-primary"></div>
                                            <div className="mt-2">กำลังโหลด...</div>
                                        </td>
                                    </tr>
                                ) : filteredProducts.length === 0 ? (
                                    <tr>
                                        <td colSpan={9} className="text-center py-5 text-muted">
                                            <i className="bi bi-inbox fs-1 d-block mb-2"></i>
                                            ไม่พบสินค้า
                                        </td>
                                    </tr>
                                ) : (
                                    filteredProducts.map((product) => {
                                        const stock = product.stock_quantity ?? 0;
                                        const stockClass = stock === 0 ? 'text-danger' : stock <= 10 ? 'text-warning' : 'text-success';
                                        return (
                                            <tr key={product.id} className={selectedProducts.has(product.id) ? 'table-active' : ''}>
                                                <td className="ps-3">
                                                    <input
                                                        type="checkbox"
                                                        className="form-check-input"
                                                        checked={selectedProducts.has(product.id)}
                                                        onChange={() => toggleSelect(product.id)}
                                                    />
                                                </td>
                                                <td>
                                                    <div className="bg-light rounded d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px', overflow: 'hidden' }}>
                                                        {product.image_url ? (
                                                            <img src={product.image_url} alt={product.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                                        ) : (
                                                            <i className="bi bi-image text-secondary"></i>
                                                        )}
                                                    </div>
                                                </td>
                                                <td>
                                                    <div className="fw-medium text-dark">{product.name}</div>
                                                    <div className="small text-muted font-monospace">{product.sku}</div>
                                                </td>
                                                <td>
                                                    <span className={`badge ${product.product_type === 'SET' ? 'bg-info text-dark' : product.product_type === 'SERVICE' ? 'bg-purple' : 'bg-light text-dark border'}`}>
                                                        {product.product_type}
                                                    </span>
                                                </td>
                                                <td className="text-end text-muted">
                                                    ฿{product.standard_cost?.toLocaleString() ?? 0}
                                                </td>
                                                <td className="text-end fw-bold text-primary">
                                                    ฿{product.standard_price?.toLocaleString() ?? 0}
                                                </td>
                                                <td className={`text-center fw-bold ${stockClass}`}>
                                                    {stock}
                                                    {stock === 0 && <i className="bi bi-exclamation-triangle ms-1"></i>}
                                                </td>
                                                <td className="text-center">
                                                    {product.is_active ? (
                                                        <span className="badge bg-success-subtle text-success rounded-pill px-3">เปิดขาย</span>
                                                    ) : (
                                                        <span className="badge bg-danger-subtle text-danger rounded-pill px-3">ปิดขาย</span>
                                                    )}
                                                </td>
                                                <td className="text-end pe-3">
                                                    <button className="btn btn-sm btn-outline-secondary" onClick={() => openEditModal(product)}>
                                                        <i className="bi bi-pencil"></i>
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Edit/Add Modal */}
            {showEditModal && editingProduct && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-lg">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    {isEditing ? `แก้ไขสินค้า: ${editingProduct.sku}` : 'เพิ่มสินค้าใหม่'}
                                </h5>
                                <button type="button" className="btn-close" onClick={() => setShowEditModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">SKU {isEditing && <span className="text-muted small">(ไม่สามารถแก้ไข)</span>}</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={editForm.sku || ''}
                                            onChange={e => setEditForm({ ...editForm, sku: e.target.value })}
                                            disabled={isEditing}
                                            placeholder="เช่น PRODUCT_001"
                                        />
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">ประเภท</label>
                                        <select
                                            className="form-select"
                                            value={editForm.product_type}
                                            onChange={e => setEditForm({ ...editForm, product_type: e.target.value })}
                                        >
                                            <option value="NORMAL">สินค้าปกติ</option>
                                            <option value="SERVICE">บริการ</option>
                                            <option value="SET">ชุดสินค้า</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="mb-3">
                                    <label className="form-label">ชื่อสินค้า</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={editForm.name || ''}
                                        onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                                        placeholder="ชื่อสินค้า"
                                    />
                                </div>

                                <div className="mb-3">
                                    <label className="form-label">รูปภาพ (URL)</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={editForm.image_url || ''}
                                        onChange={e => setEditForm({ ...editForm, image_url: e.target.value })}
                                        placeholder="https://example.com/image.jpg"
                                    />
                                </div>

                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">ต้นทุน</label>
                                        <div className="input-group">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={editForm.standard_cost || 0}
                                                onChange={e => setEditForm({ ...editForm, standard_cost: parseFloat(e.target.value) })}
                                            />
                                        </div>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">ราคาขาย</label>
                                        <div className="input-group">
                                            <span className="input-group-text">฿</span>
                                            <input
                                                type="number"
                                                className="form-control"
                                                value={editForm.standard_price || 0}
                                                onChange={e => setEditForm({ ...editForm, standard_price: parseFloat(e.target.value) })}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="form-check">
                                    <input
                                        type="checkbox"
                                        className="form-check-input"
                                        id="isActive"
                                        checked={editForm.is_active ?? true}
                                        onChange={e => setEditForm({ ...editForm, is_active: e.target.checked })}
                                    />
                                    <label className="form-check-label" htmlFor="isActive">เปิดขาย</label>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>ยกเลิก</button>
                                <button type="button" className="btn btn-primary" onClick={handleSaveProduct}>
                                    <i className="bi bi-check-lg me-1"></i>บันทึก
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Products;
