import React, { useEffect, useState } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';
import type { Product } from '../types';

const Products: React.FC = () => {
    // === Original State ===
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // === Filter State ===
    const [filterType, setFilterType] = useState<string>('NORMAL'); // Default to NORMAL (single SKU)

    // === Edit/Add Modal State ===
    // If editingProduct has an ID, it's an Edit. If ID is missing/undefined, it's a Create.
    const [editingProduct, setEditingProduct] = useState<Partial<Product> | null>(null);
    const [showEditModal, setShowEditModal] = useState<boolean>(false);
    const [editForm, setEditForm] = useState<Partial<Product>>({});

    const fetchProducts = React.useCallback(async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (filterType) params.product_type = filterType;

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

    // === Handlers ===
    const openAddModal = () => {
        setEditingProduct({}); // Empty object -> New Product
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
                // UPDATE
                await api.put(`/products/${productId}`, editForm);
            } else {
                // CREATE
                if (!editForm.sku || !editForm.name) {
                    alert("Please enter SKU and Name");
                    return;
                }
                const res = await api.post('/products', editForm);
                productId = res.data.id;
            }



            setShowEditModal(false);
            fetchProducts();
        } catch (err) {
            console.error("Failed to save product", err);
            alert("Failed to save product. " + ((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || ""));
        }
    };



    const breadcrumb = (
        <li className="breadcrumb-item active" aria-current="page">Products</li>
    );

    const isEditing = !!editingProduct?.id;

    return (
        <Layout
            title="Products"
            breadcrumb={breadcrumb}
            actions={
                <div className="d-flex gap-2">
                    <select
                        className="form-select w-auto"
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                    >
                        <option value="NORMAL">Normal Products</option>
                        <option value="SERVICE">Services</option>
                    </select>
                    <button className="btn btn-outline-primary" onClick={fetchProducts}>
                        <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                    </button>
                    <button className="btn btn-primary" onClick={openAddModal}>
                        <i className="bi bi-plus-lg me-2"></i>Add Product
                    </button>
                </div>
            }
        >
            {error && <div className="alert alert-danger">{error}</div>}

            <div className="card border-0 shadow-sm">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-4 py-3" style={{ width: '80px' }}>Image</th>
                                    <th className="py-3">Details</th>
                                    <th className="py-3">Type</th>
                                    <th className="py-3 text-end">Cost</th>
                                    <th className="py-3 text-end">Price</th>
                                    <th className="pe-4 py-3 text-center">Status</th>
                                    <th className="pe-4 py-3 text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && products.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="text-center py-5 text-muted">Loading products...</td>
                                    </tr>
                                ) : products.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="text-center py-5 text-muted">No products found</td>
                                    </tr>
                                ) : (
                                    products.map((product) => (
                                        <tr key={product.id}>
                                            <td className="ps-4">
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
                                                <span className={`badge ${product.product_type === 'SET' ? 'bg-info text-dark' : 'bg-light text-dark border'}`}>
                                                    {product.product_type}
                                                </span>
                                            </td>
                                            <td className="text-end text-muted">
                                                ฿{product.standard_cost.toLocaleString()}
                                            </td>
                                            <td className="text-end fw-bold text-primary">
                                                ฿{product.standard_price.toLocaleString()}
                                            </td>
                                            <td className="pe-4 text-center">
                                                {product.is_active ? (
                                                    <span className="badge bg-success-subtle text-success rounded-pill px-3">Active</span>
                                                ) : (
                                                    <span className="badge bg-danger-subtle text-danger rounded-pill px-3">Inactive</span>
                                                )}
                                            </td>
                                            <td className="text-end pe-4">
                                                <button className="btn btn-sm btn-outline-secondary" onClick={() => openEditModal(product)}>
                                                    <i className="bi bi-pencil"></i> Edit
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

            {/* Edit/Add Modal */}
            {showEditModal && editingProduct && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-lg">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title">
                                    {isEditing ? `Edit Product: ${editingProduct.sku}` : 'Add New Product'}
                                </h5>
                                <button type="button" className="btn-close" onClick={() => setShowEditModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">SKU {isEditing && <span className="text-muted small">(Cannot change)</span>}</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={editForm.sku || ''}
                                            onChange={e => setEditForm({ ...editForm, sku: e.target.value })}
                                            disabled={isEditing}
                                            placeholder="e.g. PRODUCT_001"
                                        />
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">Type</label>
                                        <select
                                            className="form-select"
                                            value={editForm.product_type}
                                            onChange={e => setEditForm({ ...editForm, product_type: e.target.value })}
                                        >
                                            <option value="NORMAL">Normal Product</option>
                                            <option value="SERVICE">Service</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="mb-3">
                                    <label className="form-label">Product Name</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={editForm.name || ''}
                                        onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                                        placeholder="Product Name"
                                    />
                                </div>
                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">Standard Cost</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={editForm.standard_cost || 0}
                                            onChange={e => setEditForm({ ...editForm, standard_cost: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <label className="form-label">Standard Price</label>
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={editForm.standard_price || 0}
                                            onChange={e => setEditForm({ ...editForm, standard_price: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>Cancel</button>
                                <button type="button" className="btn btn-primary" onClick={handleSaveProduct}>Save Product</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Products;
