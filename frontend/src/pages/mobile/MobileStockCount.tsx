import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import './Mobile.css';

interface StockItem {
    sku: string;
    product_name: string;
    on_hand: number;
    reserved: number;
    available: number;
}

interface CountLog {
    id: string;
    sku: string;
    counted: number;
    system: number;
    diff: number;
    time: Date;
}

const MobileStockCount: React.FC = () => {
    const navigate = useNavigate();
    const [barcode, setBarcode] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentItem, setCurrentItem] = useState<StockItem | null>(null);
    const [countValue, setCountValue] = useState('');
    const [logs, setLogs] = useState<CountLog[]>([]);
    const [todayCount, setTodayCount] = useState(0);

    const inputRef = useRef<HTMLInputElement>(null);
    const countInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (!currentItem) {
            inputRef.current?.focus();
        }
    }, [loading, currentItem]);

    const handleScan = async (e: React.FormEvent) => {
        e.preventDefault();
        const code = barcode.trim();
        if (!code) return;

        setLoading(true);
        setBarcode('');
        setCurrentItem(null);

        try {
            const { data } = await api.get('/stock/summary', {
                params: { search: code }
            });

            const items = data.items || [];
            const found = items.find((item: StockItem) =>
                item.sku.toLowerCase() === code.toLowerCase()
            );

            if (found) {
                setCurrentItem(found);
                setCountValue('');
                setTimeout(() => countInputRef.current?.focus(), 100);
            } else if (items.length > 0) {
                setCurrentItem(items[0]);
                setCountValue('');
                setTimeout(() => countInputRef.current?.focus(), 100);
            } else {
                addLog(code, 0, 0, -999);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const addLog = (sku: string, counted: number, system: number, diff: number) => {
        setLogs(prev => [{
            id: Math.random().toString(36).substr(2, 9),
            sku,
            counted,
            system,
            diff,
            time: new Date()
        }, ...prev].slice(0, 50));
    };

    const handleCount = (e: React.FormEvent) => {
        e.preventDefault();
        if (!currentItem || countValue === '') return;

        const counted = parseInt(countValue) || 0;
        const diff = counted - currentItem.on_hand;

        addLog(currentItem.sku, counted, currentItem.on_hand, diff);
        setTodayCount(prev => prev + 1);
        setCurrentItem(null);
        setCountValue('');
        inputRef.current?.focus();
    };

    const cancelCount = () => {
        setCurrentItem(null);
        setCountValue('');
        inputRef.current?.focus();
    };

    const adjustCount = (delta: number) => {
        const current = parseInt(countValue) || 0;
        const newValue = Math.max(0, current + delta);
        setCountValue(newValue.toString());
    };

    const getDiffClass = () => {
        const counted = parseInt(countValue) || 0;
        if (!currentItem) return '';
        if (counted === currentItem.on_hand) return 'match';
        if (counted > currentItem.on_hand) return 'over';
        return 'under';
    };

    return (
        <div className="mobile-container">
            {/* Header */}
            <div className="mobile-header">
                <button
                    className="mobile-header-back"
                    onClick={() => navigate('/mobile')}
                >
                    <i className="bi bi-chevron-left"></i>
                </button>
                <h1 className="mobile-header-title">
                    <i className="bi bi-clipboard-check-fill me-2" style={{ color: '#06b6d4' }}></i>
                    Stock Count
                </h1>
                <div style={{ width: 48 }}></div>
            </div>

            {/* Scan Box (when no item selected) */}
            {!currentItem && (
                <div style={{
                    background: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
                    borderRadius: 20,
                    padding: 24,
                    textAlign: 'center',
                    color: 'white',
                    marginBottom: 16
                }}>
                    <h5 style={{ marginBottom: 16, fontWeight: 600, fontSize: '1.1rem' }}>
                        <i className="bi bi-upc-scan me-2"></i>
                        Scan SKU
                    </h5>
                    <form onSubmit={handleScan}>
                        <input
                            ref={inputRef}
                            type="text"
                            className="mobile-scan-input"
                            placeholder="สแกน Barcode หรือพิมพ์ SKU"
                            value={barcode}
                            onChange={(e) => setBarcode(e.target.value)}
                            disabled={loading}
                            autoFocus
                        />
                    </form>
                    {loading && (
                        <div className="spinner-border text-light spinner-border-sm" style={{ marginTop: 16 }}></div>
                    )}
                </div>
            )}

            {/* Count Input (when item is selected) */}
            {currentItem && (
                <div className="mobile-confirm-card" style={{ marginBottom: 16 }}>
                    <div style={{
                        background: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
                        padding: 16,
                        color: 'white',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{currentItem.sku}</div>
                        <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>{currentItem.product_name || '-'}</div>
                    </div>

                    <div className="mobile-confirm-body">
                        {/* System Stock Info */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(3, 1fr)',
                            gap: 8,
                            marginBottom: 20
                        }}>
                            <div style={{
                                background: '#f1f5f9',
                                borderRadius: 12,
                                padding: 12,
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>ระบบ</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>
                                    {currentItem.on_hand}
                                </div>
                            </div>
                            <div style={{
                                background: '#fef3c7',
                                borderRadius: 12,
                                padding: 12,
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '0.75rem', color: '#92400e' }}>จอง</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#d97706' }}>
                                    {currentItem.reserved}
                                </div>
                            </div>
                            <div style={{
                                background: '#d1fae5',
                                borderRadius: 12,
                                padding: 12,
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '0.75rem', color: '#065f46' }}>ใช้ได้</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#059669' }}>
                                    {currentItem.available}
                                </div>
                            </div>
                        </div>

                        {/* Count Input with +/- */}
                        <div style={{ marginBottom: 16 }}>
                            <label style={{
                                display: 'block',
                                fontWeight: 600,
                                marginBottom: 8,
                                color: '#475569'
                            }}>
                                จำนวนที่นับได้
                            </label>
                            <div className="mobile-number-input">
                                <button
                                    type="button"
                                    className="mobile-number-btn"
                                    onClick={() => adjustCount(-1)}
                                >
                                    <i className="bi bi-dash"></i>
                                </button>
                                <input
                                    ref={countInputRef}
                                    type="number"
                                    className="mobile-number-value"
                                    placeholder="0"
                                    value={countValue}
                                    onChange={(e) => setCountValue(e.target.value)}
                                    min="0"
                                    autoFocus
                                />
                                <button
                                    type="button"
                                    className="mobile-number-btn"
                                    onClick={() => adjustCount(1)}
                                >
                                    <i className="bi bi-plus"></i>
                                </button>
                            </div>
                        </div>

                        {/* Diff Indicator */}
                        {countValue !== '' && (
                            <div className={`mobile-diff ${getDiffClass()}`}>
                                {parseInt(countValue) === currentItem.on_hand ? (
                                    <><i className="bi bi-check-circle-fill"></i> ตรงกัน</>
                                ) : parseInt(countValue) > currentItem.on_hand ? (
                                    <><i className="bi bi-arrow-up-circle-fill"></i> เกิน {parseInt(countValue) - currentItem.on_hand}</>
                                ) : (
                                    <><i className="bi bi-arrow-down-circle-fill"></i> ขาด {currentItem.on_hand - parseInt(countValue)}</>
                                )}
                            </div>
                        )}

                        {/* Actions */}
                        <div className="mobile-confirm-actions" style={{ marginTop: 16 }}>
                            <button
                                className="mobile-btn success flex-1"
                                onClick={handleCount}
                                disabled={countValue === ''}
                            >
                                <i className="bi bi-check-lg"></i>
                                บันทึก
                            </button>
                            <button
                                className="mobile-btn outline"
                                onClick={cancelCount}
                            >
                                ยกเลิก
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats */}
            <div className="mobile-stats-bar" style={{ marginBottom: 16 }}>
                <div className="mobile-stat-item">
                    <i className="bi bi-clipboard-check"></i>
                    <span>นับวันนี้</span>
                </div>
                <span className="mobile-stat-value">{todayCount}</span>
            </div>

            {/* Log History */}
            <div className="mobile-log-card">
                <div className="mobile-log-header">
                    <i className="bi bi-clock-history"></i>
                    ประวัติการนับ
                </div>
                <div className="mobile-log-list">
                    {logs.length === 0 ? (
                        <div className="mobile-empty" style={{ padding: 24 }}>
                            <i className="bi bi-inbox mobile-empty-icon"></i>
                            <p className="mobile-empty-text">ยังไม่มีรายการ</p>
                        </div>
                    ) : (
                        logs.map(log => (
                            <div key={log.id} className="mobile-log-item">
                                <div>
                                    <span style={{ fontWeight: 600 }}>{log.sku}</span>
                                    {log.diff === -999 ? (
                                        <span className="mobile-badge" style={{
                                            marginLeft: 8,
                                            background: '#ef4444',
                                            color: 'white'
                                        }}>ไม่พบ</span>
                                    ) : log.diff === 0 ? (
                                        <span className="mobile-badge" style={{
                                            marginLeft: 8,
                                            background: '#10b981',
                                            color: 'white'
                                        }}>ตรง</span>
                                    ) : log.diff > 0 ? (
                                        <span className="mobile-badge" style={{
                                            marginLeft: 8,
                                            background: '#06b6d4',
                                            color: 'white'
                                        }}>+{log.diff}</span>
                                    ) : (
                                        <span className="mobile-badge" style={{
                                            marginLeft: 8,
                                            background: '#f59e0b',
                                            color: 'white'
                                        }}>{log.diff}</span>
                                    )}
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    {log.diff !== -999 && (
                                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                            นับ: {log.counted} / ระบบ: {log.system}
                                        </div>
                                    )}
                                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                                        {log.time.toLocaleTimeString('th-TH')}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

export default MobileStockCount;
