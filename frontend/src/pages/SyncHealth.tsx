import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface SyncStatus {
    [platform: string]: {
        last_order_synced: string | null;
        last_order_id: string | null;
        external_id: string | null;
        status: 'ok' | 'stale' | 'warning' | 'no_data';
    };
}

interface HealthData {
    overall_status: 'healthy' | 'warning' | 'critical';
    sync_status: SyncStatus;
    today_summary: {
        [platform: string]: {
            total: number;
            by_status: { [key: string]: number };
        };
    };
    issues: string[];
    checked_at: string;
}

interface Gap {
    date: string;
    platform: string;
    count: number;
    issue: string;
}

const SyncHealth: React.FC = () => {
    const [health, setHealth] = useState<HealthData | null>(null);
    const [gaps, setGaps] = useState<{ gaps_found: number; gaps: Gap[] }>({ gaps_found: 0, gaps: [] });
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [healthRes, gapsRes] = await Promise.all([
                api.get('/reconciliation/health'),
                api.get('/reconciliation/gaps?days=7')
            ]);
            setHealth(healthRes.data);
            setGaps(gapsRes.data);
            setLastRefresh(new Date());
        } catch (e) {
            console.error('Failed to load sync health:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
        // Auto-refresh every 30 minutes (manual refresh available via button)
        const interval = setInterval(loadData, 30 * 60 * 1000);
        return () => clearInterval(interval);
    }, [loadData]);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'ok':
            case 'healthy':
                return 'success';
            case 'warning':
            case 'stale':
                return 'warning';
            case 'critical':
                return 'danger';
            default:
                return 'secondary';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'ok':
            case 'healthy':
                return 'bi-check-circle-fill';
            case 'warning':
            case 'stale':
                return 'bi-exclamation-triangle-fill';
            case 'critical':
                return 'danger';
            default:
                return 'bi-question-circle';
        }
    };

    const getPlatformIcon = (platform: string) => {
        switch (platform) {
            case 'tiktok':
                return { icon: '🎵', bg: 'dark', color: 'white' };
            case 'shopee':
                return { icon: '🛒', bg: 'warning', color: 'dark' };
            case 'lazada':
                return { icon: '🏪', bg: 'primary', color: 'white' };
            default:
                return { icon: '📦', bg: 'secondary', color: 'white' };
        }
    };

    const breadcrumb = (
        <>
            <li className="breadcrumb-item">ระบบ</li>
            <li className="breadcrumb-item active">สถานะ Sync</li>
        </>
    );

    return (
        <Layout title="สถานะ Sync & Data Integrity" breadcrumb={breadcrumb}>
            {/* Overall Health Card */}
            <div className="row mb-4">
                <div className="col-12">
                    <div className={`card border-0 shadow-sm bg-${health ? getStatusColor(health.overall_status) : 'secondary'} text-white`}>
                        <div className="card-body py-4">
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <h4 className="mb-1">
                                        <i className={`bi ${health ? getStatusIcon(health.overall_status) : 'bi-hourglass'} me-2`}></i>
                                        {health?.overall_status === 'healthy' && 'ระบบทำงานปกติ'}
                                        {health?.overall_status === 'warning' && 'มีข้อควรระวัง'}
                                        {health?.overall_status === 'critical' && 'พบปัญหา!'}
                                        {!health && 'กำลังโหลด...'}
                                    </h4>
                                    <small className="opacity-75">
                                        อัปเดตล่าสุด: {lastRefresh.toLocaleTimeString('th-TH')}
                                    </small>
                                </div>
                                <button
                                    className="btn btn-light"
                                    onClick={loadData}
                                    disabled={loading}
                                >
                                    <i className={`bi ${loading ? 'bi-arrow-repeat spin' : 'bi-arrow-clockwise'} me-2`}></i>
                                    รีเฟรช
                                </button>
                            </div>

                            {health?.issues && health.issues.length > 0 && (
                                <div className="mt-3 p-2 bg-white bg-opacity-25 rounded">
                                    <strong>ปัญหาที่พบ:</strong>
                                    <ul className="mb-0 mt-1">
                                        {health.issues.map((issue, idx) => (
                                            <li key={idx}>{issue}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Sync Status per Platform */}
            <div className="row g-3 mb-4">
                {health?.sync_status && Object.entries(health.sync_status).map(([platform, status]) => {
                    const pi = getPlatformIcon(platform);
                    return (
                        <div className="col-md-4" key={platform}>
                            <div className="card border-0 shadow-sm h-100">
                                <div className={`card-header bg-${pi.bg} text-${pi.color} d-flex justify-content-between align-items-center`}>
                                    <span>{pi.icon} {platform.toUpperCase()}</span>
                                    <span className={`badge bg-${getStatusColor(status.status)}`}>
                                        {status.status === 'ok' && '✓ ปกติ'}
                                        {status.status === 'stale' && '⏰ ค้าง'}
                                        {status.status === 'warning' && '⚠️ เตือน'}
                                        {status.status === 'no_data' && '❌ ไม่มีข้อมูล'}
                                    </span>
                                </div>
                                <div className="card-body">
                                    <div className="mb-2">
                                        <small className="text-muted">Order ล่าสุด:</small>
                                        <div className="fw-mono small">{status.external_id || '-'}</div>
                                    </div>
                                    <div className="mb-2">
                                        <small className="text-muted">Sync เมื่อ:</small>
                                        <div className="small">
                                            {status.last_order_synced
                                                ? new Date(status.last_order_synced).toLocaleString('th-TH')
                                                : '-'}
                                        </div>
                                    </div>
                                    {health.today_summary[platform] && (
                                        <div className="mt-3 p-2 bg-light rounded text-center">
                                            <div className="fs-4 fw-bold text-primary">
                                                {health.today_summary[platform].total.toLocaleString()}
                                            </div>
                                            <small className="text-muted">Orders วันนี้</small>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Data Gaps */}
            {gaps.gaps_found > 0 && (
                <div className="card border-danger shadow-sm mb-4">
                    <div className="card-header bg-danger text-white">
                        <i className="bi bi-exclamation-triangle me-2"></i>
                        พบช่องว่างข้อมูล ({gaps.gaps_found} รายการ)
                    </div>
                    <div className="card-body p-0">
                        <table className="table table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>วันที่</th>
                                    <th>Platform</th>
                                    <th>จำนวน Orders</th>
                                    <th>ปัญหา</th>
                                </tr>
                            </thead>
                            <tbody>
                                {gaps.gaps.map((gap, idx) => (
                                    <tr key={idx}>
                                        <td>{gap.date}</td>
                                        <td>
                                            <span className={`badge bg-${getPlatformIcon(gap.platform).bg} text-${getPlatformIcon(gap.platform).color}`}>
                                                {gap.platform}
                                            </span>
                                        </td>
                                        <td>{gap.count}</td>
                                        <td>
                                            {gap.issue === 'no_orders' && (
                                                <span className="badge bg-danger">ไม่มี Order</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Today's Summary */}
            {health?.today_summary && (
                <div className="card border-0 shadow-sm">
                    <div className="card-header bg-white">
                        <i className="bi bi-calendar-check me-2"></i>
                        สรุป Orders วันนี้ (แยกตามสถานะ)
                    </div>
                    <div className="card-body">
                        <div className="row">
                            {Object.entries(health.today_summary).map(([platform, data]) => (
                                <div className="col-md-4 mb-3" key={platform}>
                                    <h6 className="text-uppercase text-muted">{platform}</h6>
                                    <div className="d-flex flex-wrap gap-2">
                                        {Object.entries(data.by_status || {}).map(([status, count]) => (
                                            <span key={status} className="badge bg-secondary">
                                                {status}: {count}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default SyncHealth;
