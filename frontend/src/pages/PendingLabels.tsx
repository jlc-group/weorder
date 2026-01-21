import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';

interface PendingOrder {
    id: string;
    external_order_id: string;
    channel_code: string;
    status_normalized: string;
    customer_name: string;
    created_at: string;
    total_amount: number;
    item_count: number;
}

const PendingLabels: React.FC = () => {
    const [orders, setOrders] = useState<PendingOrder[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedPlatform, setSelectedPlatform] = useState<string>('ALL');
    const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
    const [isPrinting, setIsPrinting] = useState(false);
    const [isMarking, setIsMarking] = useState(false);
    const [includeShipped, setIncludeShipped] = useState(false);
    const [totalCount, setTotalCount] = useState(0);

    const loadPendingLabels = useCallback(async () => {
        setLoading(true);
        try {
            const params: Record<string, string | boolean> = { include_shipped: includeShipped };
            if (selectedPlatform !== 'ALL') {
                params.platform = selectedPlatform;
            }
            const { data } = await api.get('/orders/pending-labels', { params });
            setOrders(data.orders || []);
            setTotalCount(data.count || 0);
        } catch (error) {
            console.error('Error loading pending labels:', error);
        } finally {
            setLoading(false);
        }
    }, [selectedPlatform, includeShipped]);

    useEffect(() => {
        loadPendingLabels();
    }, [loadPendingLabels]);

    const toggleOrderSelection = (orderId: string) => {
        const newSelected = new Set(selectedOrders);
        if (newSelected.has(orderId)) {
            newSelected.delete(orderId);
        } else {
            newSelected.add(orderId);
        }
        setSelectedOrders(newSelected);
    };

    const selectAll = () => {
        if (selectedOrders.size === orders.length) {
            setSelectedOrders(new Set());
        } else {
            setSelectedOrders(new Set(orders.map(o => o.id)));
        }
    };

    const printSelectedLabels = async () => {
        if (selectedOrders.size === 0) {
            alert('กรุณาเลือก Order ที่ต้องการพิมพ์');
            return;
        }

        setIsPrinting(true);
        try {
            const ids = Array.from(selectedOrders).join(',');
            // Open PDF in new tab
            window.open(`/api/orders/batch-labels?ids=${ids}&format=pdf`, '_blank');
        } catch (error) {
            console.error('Error printing labels:', error);
            alert('เกิดข้อผิดพลาดในการพิมพ์');
        } finally {
            setIsPrinting(false);
        }
    };

    const markAsPrinted = async () => {
        if (selectedOrders.size === 0) {
            alert('กรุณาเลือก Order ที่ต้องการ Mark');
            return;
        }

        const confirmed = window.confirm(
            `ต้องการ Mark ${selectedOrders.size} orders ว่าพิมพ์แล้ว?\n\n` +
            `(ใช้สำหรับ orders ที่พิมพ์จาก Platform โดยตรง)`
        );
        if (!confirmed) return;

        setIsMarking(true);
        try {
            const { data } = await api.post('/orders/mark-printed', Array.from(selectedOrders));
            alert(data.message);
            setSelectedOrders(new Set());
            loadPendingLabels();
        } catch (error: unknown) {
            console.error('Error marking as printed:', error);
            alert('เกิดข้อผิดพลาด: ' + ((error as Error).message || 'Unknown error'));
        } finally {
            setIsMarking(false);
        }
    };

    const formatDate = (dateStr: string) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('th-TH', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getPlatformBadge = (platform: string) => {
        const colors: Record<string, string> = {
            tiktok: 'bg-gray-900 text-white',
            shopee: 'bg-orange-500 text-white',
            lazada: 'bg-blue-600 text-white',
            lnwshop: 'bg-purple-600 text-white'
        };
        return colors[platform?.toLowerCase()] || 'bg-gray-500 text-white';
    };

    const getStatusBadge = (status: string) => {
        const colors: Record<string, string> = {
            'PAID': 'bg-yellow-100 text-yellow-800',
            'PACKING': 'bg-orange-100 text-orange-800',
            'READY_TO_SHIP': 'bg-green-100 text-green-800',
            'SHIPPED': 'bg-blue-100 text-blue-800',
            'IN_TRANSIT': 'bg-purple-100 text-purple-800'
        };
        return colors[status] || 'bg-gray-100 text-gray-800';
    };

    return (
        <Layout>
            <div className="p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-800">📋 ใบปะหน้าค้าง</h1>
                        <p className="text-gray-600 mt-1">
                            Order ที่ยังไม่ได้พิมพ์ใบปะหน้าผ่านระบบ
                        </p>
                    </div>
                    <button
                        onClick={loadPendingLabels}
                        className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700"
                    >
                        🔄 รีเฟรช
                    </button>
                </div>

                {/* Filters & Actions */}
                <div className="flex flex-wrap items-center justify-between mb-4 gap-4">
                    <div className="flex items-center gap-4 flex-wrap">
                        {/* Platform Filter */}
                        <select
                            value={selectedPlatform}
                            onChange={(e) => setSelectedPlatform(e.target.value)}
                            className="px-4 py-2 border rounded-lg bg-white"
                        >
                            <option value="ALL">ทุก Platform</option>
                            <option value="tiktok">TikTok</option>
                            <option value="shopee">Shopee</option>
                            <option value="lazada">Lazada</option>
                            <option value="lnwshop">LnwShop</option>
                        </select>

                        {/* Include Shipped Toggle */}
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={includeShipped}
                                onChange={(e) => setIncludeShipped(e.target.checked)}
                                className="w-4 h-4 text-blue-600 rounded"
                            />
                            <span className="text-sm text-gray-600">
                                รวม SHIPPED/IN_TRANSIT
                            </span>
                        </label>

                        <span className="text-gray-600">
                            พบ <strong className="text-red-600">{totalCount}</strong> รายการ
                            {orders.length < totalCount && ` (แสดง ${orders.length})`}
                        </span>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-500">
                            เลือกแล้ว {selectedOrders.size} รายการ
                        </span>

                        {/* Mark as Printed Button */}
                        <button
                            onClick={markAsPrinted}
                            disabled={selectedOrders.size === 0 || isMarking}
                            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${selectedOrders.size > 0
                                ? 'bg-gray-600 hover:bg-gray-700 text-white'
                                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                }`}
                        >
                            ✓ Mark พิมพ์แล้ว
                        </button>

                        {/* Print Button */}
                        <button
                            onClick={printSelectedLabels}
                            disabled={selectedOrders.size === 0 || isPrinting}
                            className={`px-6 py-2 rounded-lg font-medium flex items-center gap-2 ${selectedOrders.size > 0
                                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                }`}
                        >
                            🖨️ พิมพ์ใบปะหน้า ({selectedOrders.size})
                        </button>
                    </div>
                </div>

                {/* Table */}
                <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                    {loading ? (
                        <div className="flex items-center justify-center p-12">
                            <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                            <span className="ml-3 text-gray-600">กำลังโหลด...</span>
                        </div>
                    ) : orders.length === 0 ? (
                        <div className="text-center p-12">
                            <div className="text-6xl mb-4">✅</div>
                            <h3 className="text-xl font-semibold text-gray-700 mb-2">ไม่มี Order ค้าง!</h3>
                            <p className="text-gray-500">ทุก Order ที่ RTS แล้วได้พิมพ์ใบปะหน้าครบแล้ว</p>
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b">
                                <tr>
                                    <th className="px-4 py-3 text-left">
                                        <input
                                            type="checkbox"
                                            checked={selectedOrders.size === orders.length && orders.length > 0}
                                            onChange={selectAll}
                                            className="w-4 h-4 text-blue-600 rounded"
                                        />
                                    </th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Platform</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Order ID</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">ลูกค้า</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">สถานะ</th>
                                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">วันที่สั่ง</th>
                                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-600">ยอด</th>
                                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-600">สินค้า</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {orders.map((order) => (
                                    <tr
                                        key={order.id}
                                        className={`hover:bg-gray-50 cursor-pointer ${selectedOrders.has(order.id) ? 'bg-blue-50' : ''
                                            }`}
                                        onClick={() => toggleOrderSelection(order.id)}
                                    >
                                        <td className="px-4 py-3">
                                            <input
                                                type="checkbox"
                                                checked={selectedOrders.has(order.id)}
                                                onChange={() => toggleOrderSelection(order.id)}
                                                onClick={(e) => e.stopPropagation()}
                                                className="w-4 h-4 text-blue-600 rounded"
                                            />
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 rounded text-xs font-medium ${getPlatformBadge(order.channel_code)}`}>
                                                {order.channel_code?.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 font-mono text-sm text-gray-700">
                                            {order.external_order_id || order.id.slice(0, 8)}
                                        </td>
                                        <td className="px-4 py-3 text-gray-800">
                                            {order.customer_name || '-'}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(order.status_normalized)}`}>
                                                {order.status_normalized}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-600">
                                            {formatDate(order.created_at)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-medium text-gray-800">
                                            ฿{order.total_amount?.toLocaleString()}
                                        </td>
                                        <td className="px-4 py-3 text-center text-gray-600">
                                            {order.item_count}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Warning Notice */}
                {orders.length > 0 && (
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <div className="flex items-start gap-3">
                            <span className="text-2xl">⚠️</span>
                            <div>
                                <h4 className="font-medium text-yellow-800">คำเตือน</h4>
                                <p className="text-sm text-yellow-700 mt-1">
                                    Order เหล่านี้อาจถูกเรียกเก็บโดย Courier แล้ว แต่ยังไม่ได้พิมพ์ใบปะหน้า
                                    กรุณาตรวจสอบและพิมพ์ให้ครบ
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default PendingLabels;
