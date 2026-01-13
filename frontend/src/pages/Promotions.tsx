import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import type { Promotion } from '../types';

const Promotions: React.FC = () => {
    const [promotions, setPromotions] = useState<Promotion[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchPromotions = async () => {
        setLoading(true);
        try {
            const res = await api.get('/promotions');
            setPromotions(res.data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPromotions();
    }, []);

    const breadcrumb = <li className="breadcrumb-item active">Promotions</li>;

    return (
        <Layout title="Promotions" breadcrumb={breadcrumb} actions={
            <button className="btn btn-primary"><i className="bi bi-plus-lg me-2"></i>New Promotion</button>
        }>
            <div className="card shadow-sm border-0">
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-4">Name</th>
                                    <th>Type</th>
                                    <th>Status</th>
                                    <th className="text-end pe-4">Duration</th>
                                </tr>
                            </thead>
                            <tbody>
                                {promotions.map((p) => (
                                    <tr key={p.id}>
                                        <td className="ps-4 fw-bold">{p.name}</td>
                                        <td><span className="badge bg-info text-dark">{p.condition_type}</span></td>
                                        <td>{p.is_active ? <span className="badge bg-success">Active</span> : <span className="badge bg-secondary">Inactive</span>}</td>
                                        <td className="text-end pe-4 small text-muted">
                                            {p.start_at ? new Date(p.start_at).toLocaleDateString() : 'Always'} - {p.end_at ? new Date(p.end_at).toLocaleDateString() : 'Forever'}
                                        </td>
                                    </tr>
                                ))}
                                {promotions.length === 0 && !loading && <tr><td colSpan={4} className="text-center py-4">No promotions found</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </Layout>
    );
};
export default Promotions;
