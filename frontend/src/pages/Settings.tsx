import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import type { PlatformConfig } from '../types';

const Settings: React.FC = () => {
    const [platforms, setPlatforms] = useState<PlatformConfig[]>([]);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);

    const fetchPlatforms = async () => {
        setLoading(true);
        try {
            const res = await api.get('/integrations/platforms');
            setPlatforms(res.data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleSyncAll = async () => {
        setSyncing(true);
        try {
            await api.post('/integrations/sync-all');
            alert('Sync started for all platforms');
        } catch (error) {
            alert('Failed to start sync');
        } finally {
            setSyncing(false);
        }
    };

    useEffect(() => {
        fetchPlatforms();
    }, []);

    const breadcrumb = <li className="breadcrumb-item active">Settings</li>;

    return (
        <Layout title="Platform Settings" breadcrumb={breadcrumb} actions={
            <button className="btn btn-outline-primary" onClick={handleSyncAll} disabled={syncing}>
                <i className={`bi bi-cloud-sync me-2 ${syncing ? 'spin' : ''}`}></i>Sync All
            </button>
        }>
            <div className="card shadow-sm border-0">
                <div className="card-header bg-white py-3">
                    <h5 className="mb-0"><i className="bi bi-plugin me-2"></i>Connected Platforms</h5>
                </div>
                <div className="card-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                            <thead className="bg-light">
                                <tr>
                                    <th className="ps-4">Platform</th>
                                    <th>Shop Name</th>
                                    <th>Status</th>
                                    <th>Sync Enabled</th>
                                    <th className="text-end pe-4">Last Sync</th>
                                </tr>
                            </thead>
                            <tbody>
                                {platforms.map((p) => (
                                    <tr key={p.id}>
                                        <td className="ps-4 text-capitalize fw-bold">{p.platform}</td>
                                        <td>{p.shop_name}</td>
                                        <td>{p.is_active ? <span className="badge bg-success">Active</span> : <span className="badge bg-secondary">Inactive</span>}</td>
                                        <td>{p.sync_enabled ? <i className="bi bi-check-circle-fill text-success"></i> : <i className="bi bi-x-circle text-muted"></i>}</td>
                                        <td className="text-end pe-4 text-muted">{p.last_sync_at ? new Date(p.last_sync_at).toLocaleString() : '-'}</td>
                                    </tr>
                                ))}
                                {platforms.length === 0 && !loading && <tr><td colSpan={5} className="text-center py-4">No platforms connected</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div className="card-footer bg-white text-end py-3">
                    <button className="btn btn-primary"><i className="bi bi-plus-lg me-2"></i>Add Connection</button>
                </div>
            </div>
        </Layout>
    );
};
export default Settings;
