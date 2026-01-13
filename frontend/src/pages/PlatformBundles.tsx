
import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Row, Col, Badge, Tabs, Tab } from 'react-bootstrap';
import axios from 'axios';
import Swal from 'sweetalert2';
import Layout from '../components/Layout';

interface Product {
    id: string;
    sku: string;
    name: string;
    // ... other fields
}

interface ListingItem {
    id?: string;
    product_id: string;
    product_sku: string;
    quantity: number;
}

interface Listing {
    id: string;
    platform: string;
    platform_sku: string;
    name: string;
    items: ListingItem[];
}

const PlatformBundles: React.FC = () => {
    const [listings, setListings] = useState<Listing[]>([]); // We need raw list now
    const [products, setProducts] = useState<Product[]>([]);

    // UI State
    const [activeTab, setActiveTab] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');

    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);

    // Form State
    const [platform, setPlatform] = useState('shopee'); // Default
    const [platformSku, setPlatformSku] = useState('');
    const [bundleName, setBundleName] = useState('');
    const [items, setItems] = useState<ListingItem[]>([]); // Current items in form

    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchListings();
        fetchProducts();
    }, []);

    const fetchListings = async () => {
        try {
            const res = await axios.get('/api/listings/');
            const data: Listing[] = res.data;
            setListings(data);
        } catch (err) {
            console.error(err);
        }
    };

    const getFilteredListings = () => {
        let filtered = listings;

        // Filter by Tab
        if (activeTab !== 'all') {
            filtered = filtered.filter(l => l.platform.toLowerCase() === activeTab);
        }

        // Filter by Search
        if (searchTerm) {
            const lower = searchTerm.toLowerCase();
            filtered = filtered.filter(l =>
                l.platform_sku.toLowerCase().includes(lower) ||
                (l.name && l.name.toLowerCase().includes(lower))
            );
        }

        return filtered;
    };

    const fetchProducts = async () => {
        try {
            // Assuming existing product endpoint
            const res = await axios.get('/api/products?per_page=100');
            setProducts(res.data.products);
        } catch (err) {
            console.error(err);
        }
    };



    const handleEdit = (listing: Listing) => {
        setPlatform(listing.platform);
        setPlatformSku(listing.platform_sku);
        setBundleName(listing.name);
        setItems(listing.items.map(i => ({
            product_id: i.product_id,
            product_sku: i.product_sku,
            quantity: i.quantity
        })));
        setEditingId(listing.id);
        setShowModal(true);
    };

    const handleOpenCreate = () => {
        setPlatform('shopee');
        setPlatformSku('');
        setBundleName('');
        setItems([{ product_id: '', product_sku: '', quantity: 1 }]);
        setEditingId(null);
        setShowModal(true);
    };

    const handleSubmit = async () => {
        if (!platformSku || items.length === 0 || !items[0].product_id) {
            Swal.fire('Error', 'Please fill all required fields', 'error');
            return;
        }

        // Validate items
        const validItems = items.filter(i => i.product_id && i.quantity > 0).map(i => ({
            product_id: i.product_id,
            quantity: i.quantity
        }));

        if (validItems.length === 0) {
            Swal.fire('Error', 'At least one valid product component is required', 'error');
            return;
        }

        setLoading(true);
        try {
            if (editingId) {
                // UPDATE
                await axios.put(`/api/listings/${editingId}`, {
                    platform,
                    platform_sku: platformSku,
                    name: bundleName || platformSku,
                    items: validItems
                });
                Swal.fire('Success', 'Listing updated successfully', 'success');
            } else {
                // CREATE
                await axios.post('/api/listings/', {
                    platform,
                    platform_sku: platformSku,
                    name: bundleName || platformSku,
                    items: validItems
                });
                Swal.fire('Success', 'Listing created successfully', 'success');
            }

            setShowModal(false);
            fetchListings();

        } catch (err: any) {
            Swal.fire('Error', err.response?.data?.detail || 'Failed to save listing', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        const confirm = await Swal.fire({
            title: 'Are you sure?',
            text: "Delete this mapping?",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete it!'
        });

        if (confirm.isConfirmed) {
            try {
                await axios.delete(`/api/listings/${id}`);
                fetchListings();
                Swal.fire('Deleted', 'Listing deleted', 'success');
            } catch (err) {
                Swal.fire('Error', 'Failed to delete listing', 'error');
            }
        }
    };

    // Helper to add item row in form
    const addItemRow = () => {
        setItems([...items, { product_id: '', product_sku: '', quantity: 1 }]);
    };

    const updateItemRow = (index: number, field: keyof ListingItem, value: any) => {
        const newItems = [...items];
        newItems[index] = { ...newItems[index], [field]: value };
        setItems(newItems);
    };

    const removeItemRow = (index: number) => {
        const newItems = [...items];
        newItems.splice(index, 1);
        setItems(newItems);
    };

    const handleAutoImport = async () => {
        setLoading(true);
        try {
            const res = await axios.post('/api/listings/import-from-history');
            const { imported, skipped } = res.data;
            Swal.fire(
                'Imported',
                `Successfully imported ${imported} listings. (Skipped ${skipped} existing)`,
                'success'
            );
            fetchListings();
        } catch (err) {
            Swal.fire('Error', 'Failed to import listings', 'error');
        } finally {
            setLoading(false);
        }
    };

    const breadcrumb = (
        <li className="breadcrumb-item active" aria-current="page">Platform Bundles</li>
    );

    return (
        <Layout
            title="Platform Bundles"
            breadcrumb={breadcrumb}
        >
            <div className="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1 className="h3 mb-0 text-gray-800">Platform Bundles</h1>
                    <p className="text-muted mb-0">Map platform listings (SKUs) to inventory products.</p>
                </div>
                <div>
                    <Button variant="info" className="me-2" onClick={handleAutoImport} disabled={loading}>
                        <i className="fas fa-magic me-1"></i> Auto Import
                    </Button>
                    <Button variant="primary" onClick={handleOpenCreate}>
                        <i className="fas fa-plus me-1"></i> Create New Bundle
                    </Button>
                </div>
            </div>

            <Card className="shadow mb-4">
                <Card.Header className="py-3 bg-white">
                    <Tabs
                        activeKey={activeTab}
                        onSelect={(k) => setActiveTab(k || 'all')}
                        className="mb-3"
                    >
                        <Tab eventKey="all" title="All Platforms" />
                        <Tab eventKey="shopee" title="Shopee" />
                        <Tab eventKey="lazada" title="Lazada" />
                        <Tab eventKey="tiktok" title="TikTok" />
                    </Tabs>

                    <Row>
                        <Col md={6}>
                            <Form.Control
                                type="text"
                                placeholder="Search bundle name or SKU..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </Col>
                        <Col md={6} className="text-end text-muted small mt-2">
                            Total: {getFilteredListings().length} bundles
                        </Col>
                    </Row>
                </Card.Header>
                <Card.Body className="p-0">
                    <Table responsive hover className="mb-0 align-middle">
                        <thead className="bg-light">
                            <tr>
                                <th className="ps-4">Platform</th>
                                <th>Platform SKU</th>
                                <th>Bundle Name</th>
                                <th>Components</th>
                                <th className="text-end pe-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {getFilteredListings().map((listing) => (
                                <tr key={listing.id}>
                                    <td className="ps-4">
                                        <Badge bg={
                                            listing.platform === 'shopee' ? 'warning' :
                                                listing.platform === 'lazada' ? 'primary' : 'dark'
                                        }>
                                            {listing.platform.toUpperCase()}
                                        </Badge>
                                    </td>
                                    <td className="fw-bold text-dark">{listing.platform_sku}</td>
                                    <td>{listing.name || '-'}</td>
                                    <td>
                                        <ul className="list-unstyled mb-0 small">
                                            {listing.items.map((item, idx) => (
                                                <li key={idx} className="text-secondary">
                                                    <span className="fw-bold">{item.quantity}x</span> {item.product_sku || 'Unknown'}
                                                </li>
                                            ))}
                                        </ul>
                                    </td>
                                    <td className="text-end pe-4">
                                        <Button
                                            variant="outline-primary"
                                            size="sm"
                                            className="me-2"
                                            onClick={() => handleEdit(listing)}
                                        >
                                            <i className="fas fa-edit"></i>
                                        </Button>
                                        <Button
                                            variant="outline-danger"
                                            size="sm"
                                            onClick={() => handleDelete(listing.id)}
                                        >
                                            <i className="fas fa-trash"></i>
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                            {getFilteredListings().length === 0 && (
                                <tr>
                                    <td colSpan={5} className="text-center py-5 text-muted">
                                        No bundles found. Try adjusting filters or create a new one.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>

            {/* Create/Edit Modal */}
            <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" backdrop="static">
                <Modal.Header closeButton>
                    <Modal.Title>{editingId ? 'Edit Bundle' : 'Create New Bundle'}</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <Row className="mb-3">
                        <Col md={4}>
                            <Form.Group>
                                <Form.Label>Platform</Form.Label>
                                <Form.Select
                                    value={platform}
                                    onChange={(e) => setPlatform(e.target.value)}
                                    disabled={!!editingId} // Locked in Edit mode to prevent key change issues
                                >
                                    <option value="shopee">Shopee</option>
                                    <option value="lazada">Lazada</option>
                                    <option value="tiktok">TikTok</option>
                                </Form.Select>
                            </Form.Group>
                        </Col>
                        <Col md={8}>
                            <Form.Group>
                                <Form.Label>Platform SKU (Must match exactly)</Form.Label>
                                <Form.Control
                                    type="text"
                                    value={platformSku}
                                    onChange={(e) => setPlatformSku(e.target.value)}
                                    placeholder="e.g. DUO-JULAHERB-01"
                                    disabled={!!editingId} // Locked in Edit mode
                                />
                            </Form.Group>
                        </Col>
                    </Row>
                    <Form.Group className="mb-4">
                        <Form.Label>Bundle Name (Internal)</Form.Label>
                        <Form.Control
                            type="text"
                            value={bundleName}
                            onChange={(e) => setBundleName(e.target.value)}
                            placeholder="e.g. Julaherb Duo Set (2 pcs)"
                        />
                    </Form.Group>

                    <h6 className="mb-3 border-bottom pb-2">Bundle Components</h6>
                    {items.map((item, index) => (
                        <Row key={index} className="mb-2 align-items-end">
                            <Col md={7}>
                                <Form.Group>
                                    <Form.Label className="small text-muted">Product</Form.Label>
                                    <Form.Select
                                        value={item.product_id}
                                        onChange={(e) => updateItemRow(index, 'product_id', e.target.value)}
                                    >
                                        <option value="">Select Master Product...</option>
                                        {products.map(p => (
                                            <option key={p.id} value={p.id}>
                                                {p.sku} - {p.name}
                                            </option>
                                        ))}
                                    </Form.Select>
                                </Form.Group>
                            </Col>
                            <Col md={3}>
                                <Form.Group>
                                    <Form.Label className="small text-muted">Quantity</Form.Label>
                                    <Form.Control
                                        type="number"
                                        min="1"
                                        value={item.quantity}
                                        onChange={(e) => updateItemRow(index, 'quantity', parseInt(e.target.value))}
                                    />
                                </Form.Group>
                            </Col>
                            <Col md={2}>
                                <Button
                                    variant="outline-danger"
                                    size="sm"
                                    className="w-100"
                                    onClick={() => removeItemRow(index)}
                                    disabled={items.length === 1}
                                >
                                    Remove
                                </Button>
                            </Col>
                        </Row>
                    ))}

                    <div className="mt-3">
                        <Button variant="outline-primary" size="sm" onClick={addItemRow}>
                            <i className="fas fa-plus me-1"></i> Add Another Component
                        </Button>
                    </div>

                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowModal(false)}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSubmit} disabled={loading}>
                        {loading ? 'Saving...' : (editingId ? 'Update Listing' : 'Create Listing')}
                    </Button>
                </Modal.Footer>
            </Modal>
        </Layout>
    );
};

export default PlatformBundles;

