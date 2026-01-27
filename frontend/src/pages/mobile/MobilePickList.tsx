import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import './Mobile.css';

interface PickItem {
    sku: string;
    product_name: string;
    total_quantity: number;
    order_count: number;
}

const MobilePickList: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [items, setItems] = useState<PickItem[]>([]);
    const [orderCount, setOrderCount] = useState(0);
    const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());

    const fetchPickList = async () => {
        setLoading(true);
        try {
            const { data } = await api.get('/orders/pick-list-summary', {
                params: { status: 'PAID' }
            });

            setItems(data.items || []);
            setOrderCount(data.order_count || 0);
            setCheckedItems(new Set());
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPickList();
    }, []);

    const toggleCheck = (sku: string) => {
        setCheckedItems(prev => {
            const newSet = new Set(prev);
            if (newSet.has(sku)) {
                newSet.delete(sku);
            } else {
                newSet.add(sku);
            }
            return newSet;
        });
    };

    const progress = items.length > 0 ? Math.round((checkedItems.size / items.length) * 100) : 0;
    const totalQty = items.reduce((sum, i) => sum + i.total_quantity, 0);

    const handlePrint = () => {
        const printWindow = window.open('', '_blank');
        if (printWindow) {
            const rows = items.map((item, idx) => `
                <tr>
                    <td style="text-align: center;">${idx + 1}</td>
                    <td>
                        <div style="font-weight: bold;">${item.sku}</div>
                        <div style="font-size: 12px; color: #666;">${item.product_name}</div>
                    </td>
                    <td style="text-align: center; font-size: 18px; font-weight: bold;">${item.total_quantity}</td>
                    <td><div style="width: 20px; height: 20px; border: 1px solid #ccc;"></div></td>
                </tr>
            `).join('');

            printWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Pick List</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                        th, td { border: 1px solid #ddd; padding: 12px; }
                        th { background-color: #f2f2f2; text-align: left; }
                        .header { text-align: center; margin-bottom: 20px; }
                        @media print { .no-print { display: none; } }
                    </style>
                </head>
                <body>
                    <button class="no-print" onclick="window.print()" style="position: fixed; top: 20px; right: 20px; padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;">🖨️ พิมพ์</button>
                    <div class="header">
                        <h2>ใบสรุปรายการสินค้า (Pick List)</h2>
                        <p>สำหรับ ${orderCount} ออเดอร์ | รวมสินค้าทั้งหมด ${totalQty} ชิ้น</p>
                        <p style="font-size: 12px; color: #666;">พิมพ์เมื่อ: ${new Date().toLocaleString('th-TH')}</p>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 50px; text-align: center;">#</th>
                                <th>สินค้า</th>
                                <th style="width: 100px; text-align: center;">จำนวน</th>
                                <th style="width: 50px;">Check</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </body>
                </html>
            `);
            printWindow.document.close();
        }
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
                    <i className="bi bi-list-check me-2" style={{ color: '#3b82f6' }}></i>
                    Pick List
                </h1>
                <button
                    className="mobile-header-back"
                    onClick={fetchPickList}
                    disabled={loading}
                >
                    <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                </button>
            </div>

            {/* Stats Header */}
            <div style={{
                background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                borderRadius: 16,
                padding: 16,
                color: 'white',
                marginBottom: 16
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div>
                        <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>Orders</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{orderCount}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>SKUs</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{items.length}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>ชิ้น</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{totalQty}</div>
                    </div>
                </div>

                {/* Progress Bar */}
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                        <span>หยิบแล้ว {checkedItems.size}/{items.length}</span>
                        <span>{progress}%</span>
                    </div>
                    <div className="mobile-progress">
                        <div className="mobile-progress-bar" style={{ width: `${progress}%` }}></div>
                    </div>
                </div>
            </div>

            {/* Pick List Items */}
            {loading ? (
                <div className="mobile-empty">
                    <div className="spinner-border text-primary"></div>
                    <p className="mobile-empty-text" style={{ marginTop: 12 }}>กำลังโหลด...</p>
                </div>
            ) : items.length === 0 ? (
                <div className="mobile-empty">
                    <i className="bi bi-inbox mobile-empty-icon"></i>
                    <p className="mobile-empty-text">ไม่มีรายการที่ต้องหยิบ</p>
                </div>
            ) : (
                <div className="mobile-log-card" style={{ marginBottom: 16 }}>
                    {items.map((item) => (
                        <div
                            key={item.sku}
                            className={`mobile-pick-item ${checkedItems.has(item.sku) ? 'checked' : ''}`}
                            onClick={() => toggleCheck(item.sku)}
                        >
                            <div className="mobile-pick-checkbox">
                                {checkedItems.has(item.sku) ? (
                                    <i className="bi bi-check-lg"></i>
                                ) : (
                                    <i className="bi bi-box" style={{ color: '#94a3b8' }}></i>
                                )}
                            </div>
                            <div className="mobile-pick-info">
                                <div className="mobile-pick-sku">{item.sku}</div>
                                <div className="mobile-pick-name">{item.product_name || '-'}</div>
                            </div>
                            <div className="mobile-pick-qty">
                                <div className="mobile-pick-qty-value">{item.total_quantity}</div>
                                <div className="mobile-pick-qty-label">{item.order_count} orders</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Print Button */}
            {items.length > 0 && (
                <button className="mobile-btn primary full" onClick={handlePrint}>
                    <i className="bi bi-printer"></i>
                    พิมพ์ใบหยิบ
                </button>
            )}
        </div>
    );
};

export default MobilePickList;
