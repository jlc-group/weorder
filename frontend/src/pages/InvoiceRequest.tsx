import React, { useState, useCallback } from 'react';
import api from '../api/client';

interface InvoiceStatus {
    order_id: string;
    external_order_id: string | null;
    has_request: boolean;
    can_request?: boolean;
    status?: string;
    invoice_name?: string;
    tax_id?: string;
    invoice_number?: string;
    invoice_date?: string;
    can_download?: boolean;
    download_url?: string;
    rejected_reason?: string;
    message: string;
    order_status?: string;
    deadline_passed?: boolean;
}

const InvoiceRequest: React.FC = () => {
    const [step, setStep] = useState<'search' | 'form' | 'status'>('search');
    const [orderId, setOrderId] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [statusData, setStatusData] = useState<InvoiceStatus | null>(null);

    // Form fields
    const [profileType, setProfileType] = useState<'PERSONAL' | 'COMPANY'>('PERSONAL');
    const [invoiceName, setInvoiceName] = useState('');
    const [taxId, setTaxId] = useState('');

    const [branchType, setBranchType] = useState<'HQ' | 'BRANCH'>('HQ');
    const [branchNumber, setBranchNumber] = useState('');
    const [addressLine1, setAddressLine1] = useState('');
    const [addressLine2, setAddressLine2] = useState('');
    const [subdistrict, setSubdistrict] = useState('');
    const [district, setDistrict] = useState('');
    const [province, setProvince] = useState('');
    const [postalCode, setPostalCode] = useState('');
    const [phone, setPhone] = useState('');
    const [email, setEmail] = useState('');

    const [autofillLoading, setAutofillLoading] = useState(false);

    const checkOrder = useCallback(async () => {
        if (!orderId.trim()) {
            setError('กรุณากรอกเลขที่คำสั่งซื้อ');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const { data } = await api.get(`/invoice-request/check/${orderId.trim()}`);
            setStatusData(data);

            if (data.has_request) {
                setStep('status');
            } else if (data.can_request) {
                setStep('form');
            } else {
                setError(data.message || 'ไม่สามารถขอใบกำกับภาษีได้');
            }
        } catch (e: unknown) {
            const err = e as { response?: { data?: { detail?: string } } };
            setError(err.response?.data?.detail || 'ไม่พบคำสั่งซื้อนี้ในระบบ');
        } finally {
            setLoading(false);
        }
    }, [orderId]);

    const handleLookup = async (type: 'TAX_ID' | 'PHONE', value: string) => {
        if (!value || value.length < 5) return;

        // Don't lookup if we already have name filled (assume user might be editing)
        // Or should we? Let's only lookup if name is empty OR user explicitly wants to?
        // Let's do it if invoiceName is empty TO AVOID OVERWRITING user input if they started typing.
        if (invoiceName) return;

        setAutofillLoading(true);
        try {
            const params = type === 'TAX_ID'
                ? { tax_id: value }
                : { phone: value };

            const { data } = await api.get('/invoice-request/lookup', { params });

            if (data.found) {
                // Autofill
                setProfileType(data.profile_type as any);
                setInvoiceName(data.invoice_name || '');
                if (data.tax_id) setTaxId(data.tax_id); // In case lookup by phone
                if (data.phone) setPhone(data.phone);   // In case lookup by tax

                setBranchType(data.branch === '00000' ? 'HQ' : 'BRANCH');
                if (data.branch !== '00000') setBranchNumber(data.branch || '');

                setAddressLine1(data.address_line1 || '');
                setAddressLine2(data.address_line2 || '');
                setSubdistrict(data.subdistrict || '');
                setDistrict(data.district || '');
                setProvince(data.province || '');
                setPostalCode(data.postal_code || '');
                setEmail(data.email || '');

                // Show small success indicator?
            }
        } catch (error) {
            console.error("Autofill failed", error);
        } finally {
            setAutofillLoading(false);
        }
    };

    const submitRequest = async () => {
        // Validate
        if (!invoiceName.trim()) {
            setError('กรุณากรอกชื่อสำหรับออกใบกำกับภาษี');
            return;
        }
        if (!taxId.trim() || taxId.replace(/\D/g, '').length !== 13) {
            setError('กรุณากรอกเลขประจำตัวผู้เสียภาษี 13 หลัก');
            return;
        }
        if (!addressLine1.trim()) {
            setError('กรุณากรอกที่อยู่');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const finalBranch = branchType === 'HQ' ? '00000' : branchNumber.padStart(5, '0');

            await api.post('/invoice-request', {
                order_id: orderId.trim(),
                profile_type: profileType,
                invoice_name: invoiceName.trim(),
                tax_id: taxId.replace(/\D/g, ''),
                branch: finalBranch,
                address_line1: addressLine1.trim(),
                address_line2: addressLine2.trim() || null,
                subdistrict: subdistrict.trim() || null,
                district: district.trim() || null,
                province: province.trim() || null,
                postal_code: postalCode.trim() || null,
                phone: phone.trim() || null,
                email: email.trim() || null
            });

            // Refresh status
            checkOrder();
        } catch (e: unknown) {
            const err = e as { response?: { data?: { detail?: string } } };
            setError(err.response?.data?.detail || 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง');
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setStep('search');
        setOrderId('');
        setStatusData(null);
        setError('');
        setInvoiceName('');
        setTaxId('');

        setBranchType('HQ');
        setBranchNumber('');
        setAddressLine1('');
        setAddressLine2('');
        setSubdistrict('');
        setDistrict('');
        setProvince('');
        setPostalCode('');
        setPhone('');
        setEmail('');
        setProfileType('PERSONAL');
    };



    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: '40px 20px',
            fontFamily: "'Sarabun', sans-serif"
        }}>
            <div style={{
                maxWidth: '600px',
                margin: '0 auto',
                background: 'white',
                borderRadius: '16px',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                overflow: 'hidden'
            }}>
                {/* Header */}
                <div style={{
                    background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                    padding: '30px',
                    textAlign: 'center',
                    color: 'white'
                }}>
                    <h1 style={{ margin: 0, fontSize: '24px' }}>🧾 ขอใบกำกับภาษี</h1>
                    <p style={{ margin: '10px 0 0', opacity: 0.9, fontSize: '14px' }}>
                        บริษัท เจแอลซี กรุ๊ป จำกัด
                    </p>
                </div>

                <div style={{ padding: '30px' }}>
                    {/* Error Message */}
                    {error && (
                        <div style={{
                            background: '#fef2f2',
                            border: '1px solid #fecaca',
                            color: '#dc2626',
                            padding: '12px 16px',
                            borderRadius: '8px',
                            marginBottom: '20px'
                        }}>
                            ⚠️ {error}
                        </div>
                    )}

                    {/* Step 1: Search Order */}
                    {step === 'search' && (
                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
                                เลขที่คำสั่งซื้อ
                            </label>
                            <input
                                type="text"
                                value={orderId}
                                onChange={(e) => setOrderId(e.target.value)}
                                placeholder="เช่น 581942690190755510"
                                style={{
                                    width: '100%',
                                    padding: '14px',
                                    fontSize: '16px',
                                    border: '2px solid #e5e7eb',
                                    borderRadius: '8px',
                                    boxSizing: 'border-box'
                                }}
                                onKeyDown={(e) => e.key === 'Enter' && checkOrder()}
                            />
                            <p style={{ color: '#6b7280', fontSize: '13px', marginTop: '8px' }}>
                                📌 สามารถขอใบกำกับภาษีได้ภายใน 30 วันหลังรับสินค้า
                            </p>
                            <button
                                onClick={checkOrder}
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    marginTop: '20px',
                                    padding: '16px',
                                    fontSize: '16px',
                                    fontWeight: 600,
                                    background: loading ? '#9ca3af' : '#2563eb',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: loading ? 'not-allowed' : 'pointer'
                                }}
                            >
                                {loading ? '⏳ กำลังตรวจสอบ...' : '🔍 ตรวจสอบคำสั่งซื้อ'}
                            </button>
                        </div>
                    )}

                    {/* Step 2: Form */}
                    {step === 'form' && (
                        <div>
                            <div style={{ marginBottom: '20px', padding: '12px', background: '#f0fdf4', borderRadius: '8px' }}>
                                ✅ คำสั่งซื้อ: <strong>{statusData?.external_order_id || orderId}</strong>
                            </div>

                            {/* Profile Type */}
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>ประเภท</label>
                                <div style={{ display: 'flex', gap: '16px' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                        <input
                                            type="radio"
                                            checked={profileType === 'PERSONAL'}
                                            onChange={() => setProfileType('PERSONAL')}
                                        />
                                        บุคคลธรรมดา
                                    </label>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                        <input
                                            type="radio"
                                            checked={profileType === 'COMPANY'}
                                            onChange={() => setProfileType('COMPANY')}
                                        />
                                        นิติบุคคล
                                    </label>
                                </div>
                            </div>

                            {/* Invoice Name */}
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
                                    {profileType === 'COMPANY' ? 'ชื่อบริษัท *' : 'ชื่อ-นามสกุล *'}
                                </label>
                                <input
                                    type="text"
                                    value={invoiceName}
                                    onChange={(e) => setInvoiceName(e.target.value)}
                                    placeholder={profileType === 'COMPANY' ? 'เช่น บริษัท ABC จำกัด' : 'เช่น นายสมชาย ใจดี'}
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        border: '2px solid #e5e7eb',
                                        borderRadius: '8px',
                                        boxSizing: 'border-box'
                                    }}
                                />
                            </div>

                            {/* Tax ID */}
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
                                    เลขประจำตัวผู้เสียภาษี (13 หลัก) *
                                    {autofillLoading && <span style={{ marginLeft: '10px', fontSize: '12px', color: '#2563eb' }}>⏳ กำลังค้นหาข้อมูลเก่า...</span>}
                                </label>
                                <input
                                    type="text"
                                    value={taxId}
                                    onChange={(e) => setTaxId(e.target.value.replace(/\D/g, '').slice(0, 13))}
                                    onBlur={(e) => handleLookup('TAX_ID', e.target.value)}
                                    placeholder="0123456789012"
                                    maxLength={13}
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        border: '2px solid #e5e7eb',
                                        borderRadius: '8px',
                                        boxSizing: 'border-box',
                                        fontFamily: 'monospace',
                                        letterSpacing: '2px'
                                    }}
                                />
                            </div>

                            {/* Branch (only for company) */}
                            {profileType === 'COMPANY' && (
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>สาขา</label>
                                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                            <input
                                                type="radio"
                                                checked={branchType === 'HQ'}
                                                onChange={() => setBranchType('HQ')}
                                            />
                                            สำนักงานใหญ่
                                        </label>
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                            <input
                                                type="radio"
                                                checked={branchType === 'BRANCH'}
                                                onChange={() => setBranchType('BRANCH')}
                                            />
                                            สาขา
                                        </label>
                                        {branchType === 'BRANCH' && (
                                            <input
                                                type="text"
                                                value={branchNumber}
                                                onChange={(e) => setBranchNumber(e.target.value.replace(/\D/g, '').slice(0, 5))}
                                                placeholder="00001"
                                                maxLength={5}
                                                style={{
                                                    width: '100px',
                                                    padding: '8px',
                                                    border: '2px solid #e5e7eb',
                                                    borderRadius: '8px'
                                                }}
                                            />
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Address */}
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>ที่อยู่ *</label>
                                <input
                                    type="text"
                                    value={addressLine1}
                                    onChange={(e) => setAddressLine1(e.target.value)}
                                    placeholder="บ้านเลขที่ ถนน ซอย"
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        border: '2px solid #e5e7eb',
                                        borderRadius: '8px',
                                        marginBottom: '8px',
                                        boxSizing: 'border-box'
                                    }}
                                />
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                                    <input
                                        type="text"
                                        value={subdistrict}
                                        onChange={(e) => setSubdistrict(e.target.value)}
                                        placeholder="แขวง/ตำบล"
                                        style={{
                                            padding: '12px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <input
                                        type="text"
                                        value={district}
                                        onChange={(e) => setDistrict(e.target.value)}
                                        placeholder="เขต/อำเภอ"
                                        style={{
                                            padding: '12px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <input
                                        type="text"
                                        value={province}
                                        onChange={(e) => setProvince(e.target.value)}
                                        placeholder="จังหวัด"
                                        style={{
                                            padding: '12px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <input
                                        type="text"
                                        value={postalCode}
                                        onChange={(e) => setPostalCode(e.target.value.replace(/\D/g, '').slice(0, 5))}
                                        placeholder="รหัสไปรษณีย์"
                                        maxLength={5}
                                        style={{
                                            padding: '12px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px'
                                        }}
                                    />
                                </div>
                            </div>

                            {/* Contact */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>เบอร์โทร</label>
                                    <input
                                        type="tel"
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                        onBlur={(e) => handleLookup('PHONE', e.target.value)}
                                        placeholder="0812345678"
                                        style={{
                                            width: '100%',
                                            padding: '12px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px',
                                            boxSizing: 'border-box'
                                        }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>อีเมล</label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="email@example.com"
                                        style={{
                                            width: '100%',
                                            padding: '12px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px',
                                            boxSizing: 'border-box'
                                        }}
                                    />
                                </div>
                            </div>

                            {/* Actions */}
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button
                                    onClick={resetForm}
                                    style={{
                                        flex: 1,
                                        padding: '14px',
                                        fontSize: '16px',
                                        background: '#f3f4f6',
                                        color: '#374151',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    ← ย้อนกลับ
                                </button>
                                <button
                                    onClick={submitRequest}
                                    disabled={loading}
                                    style={{
                                        flex: 2,
                                        padding: '14px',
                                        fontSize: '16px',
                                        fontWeight: 600,
                                        background: loading ? '#9ca3af' : '#16a34a',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '8px',
                                        cursor: loading ? 'not-allowed' : 'pointer'
                                    }}
                                >
                                    {loading ? '⏳ กำลังส่ง...' : '✓ ส่งคำขอใบกำกับภาษี'}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Step 3: Status */}
                    {step === 'status' && statusData && (
                        <div style={{ textAlign: 'center' }}>
                            {/* Status Icon */}
                            <div style={{
                                fontSize: '64px',
                                marginBottom: '16px'
                            }}>
                                {statusData.status === 'PENDING' && '⏳'}
                                {statusData.status === 'ISSUED' && '✅'}
                                {statusData.status === 'REJECTED' && '❌'}
                            </div>

                            {/* Status Text */}
                            <h2 style={{
                                margin: '0 0 8px',
                                color: statusData.status === 'ISSUED' ? '#16a34a' :
                                    statusData.status === 'REJECTED' ? '#dc2626' : '#d97706'
                            }}>
                                {statusData.status === 'PENDING' && 'รอดำเนินการ'}
                                {statusData.status === 'ISSUED' && 'ออกใบกำกับภาษีแล้ว'}
                                {statusData.status === 'REJECTED' && 'คำขอถูกปฏิเสธ'}
                            </h2>

                            <p style={{ color: '#6b7280', marginBottom: '24px' }}>
                                {statusData.message}
                            </p>

                            {/* Invoice Details */}
                            <div style={{
                                background: '#f9fafb',
                                borderRadius: '12px',
                                padding: '20px',
                                textAlign: 'left',
                                marginBottom: '24px'
                            }}>
                                <div style={{ marginBottom: '12px' }}>
                                    <span style={{ color: '#6b7280' }}>เลขที่คำสั่งซื้อ:</span>
                                    <strong style={{ marginLeft: '8px' }}>{statusData.external_order_id || orderId}</strong>
                                </div>
                                {statusData.invoice_name && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <span style={{ color: '#6b7280' }}>ชื่อ:</span>
                                        <strong style={{ marginLeft: '8px' }}>{statusData.invoice_name}</strong>
                                    </div>
                                )}
                                {statusData.tax_id && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <span style={{ color: '#6b7280' }}>เลขผู้เสียภาษี:</span>
                                        <strong style={{ marginLeft: '8px' }}>{statusData.tax_id}</strong>
                                    </div>
                                )}
                                {statusData.invoice_number && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <span style={{ color: '#6b7280' }}>เลขที่ใบกำกับ:</span>
                                        <strong style={{ marginLeft: '8px', color: '#2563eb' }}>{statusData.invoice_number}</strong>
                                    </div>
                                )}
                                {statusData.invoice_date && (
                                    <div>
                                        <span style={{ color: '#6b7280' }}>วันที่ออก:</span>
                                        <strong style={{ marginLeft: '8px' }}>{statusData.invoice_date}</strong>
                                    </div>
                                )}
                            </div>

                            {/* Download Button */}
                            {statusData.can_download && statusData.download_url && (
                                <a
                                    href={`/api${statusData.download_url}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                        display: 'inline-block',
                                        padding: '16px 32px',
                                        fontSize: '16px',
                                        fontWeight: 600,
                                        background: '#2563eb',
                                        color: 'white',
                                        textDecoration: 'none',
                                        borderRadius: '8px',
                                        marginBottom: '16px'
                                    }}
                                >
                                    📄 ดาวน์โหลดใบกำกับภาษี
                                </a>
                            )}

                            <button
                                onClick={resetForm}
                                style={{
                                    display: 'block',
                                    width: '100%',
                                    padding: '14px',
                                    fontSize: '16px',
                                    background: '#f3f4f6',
                                    color: '#374151',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    marginTop: '16px'
                                }}
                            >
                                ← ตรวจสอบคำสั่งซื้ออื่น
                            </button>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '20px',
                    textAlign: 'center',
                    background: '#f9fafb',
                    borderTop: '1px solid #e5e7eb',
                    color: '#6b7280',
                    fontSize: '13px'
                }}>
                    © 2026 บริษัท เจแอลซี กรุ๊ป จำกัด | เลขผู้เสียภาษี 0105552137425
                </div>
            </div>
        </div>
    );
};

export default InvoiceRequest;
