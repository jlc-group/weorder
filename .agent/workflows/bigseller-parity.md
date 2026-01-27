---
description: BigSeller Feature Parity Checklist - ต้องตรวจสอบก่อนบอกว่า "เสร็จ"
---

# BigSeller Feature Parity Checklist

## 🎯 หลักการ
**ถ้า BigSeller ทำได้ → WeOrder ต้องทำได้**

ก่อนบอกว่างานเสร็จ ต้องเช็ค checklist นี้ก่อน

---

## 📦 Order Management (การจัดการออเดอร์)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| View all orders from TikTok/Shopee/Lazada | ✅ | ✅ | DONE |
| Filter orders by status | ✅ | ✅ | DONE |
| Filter orders by date | ✅ | ✅ | DONE |
| Filter orders by platform | ✅ | ✅ | DONE |
| Order detail view | ✅ | ✅ | DONE |
| Search by order ID / tracking | ✅ | ✅ | DONE |
| Bulk select orders | ✅ | ✅ | DONE |
| Export orders to Excel | ✅ | ✅ | DONE |

---

## 🏭 Packing Workflow (การแพ็คสินค้า)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| Pick list generation | ✅ | ✅ | DONE |
| Scan to pack | ✅ | ✅ | DONE |
| Print shipping labels | ✅ | ✅ | DONE |
| Batch print labels | ✅ | ✅ | DONE |
| Auto arrange shipment (RTS) | ✅ | ✅ | DONE |
| Packing station UI | ✅ | ✅ | DONE |

---

## 🏷️ Label Printing (พิมพ์ใบปะหน้า)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| TikTok label | ✅ | ✅ | DONE |
| Shopee label | ✅ | ✅ | DONE |
| Lazada label | ✅ | ✅ | DONE |
| Merge labels to single PDF | ✅ | ✅ | DONE |
| A6 format support | ✅ | ✅ | DONE |
| Print queue management | ✅ | ✅ | DONE |

---

## 📊 Stock/Inventory (สต็อกสินค้า)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| Stock quantity view | ✅ | ✅ | DONE |
| Stock movement history | ✅ | ✅ | DONE |
| Stock card (รายการเคลื่อนไหว) | ✅ | ✅ | DONE |
| Auto deduct on ship | ✅ | ✅ | DONE |
| Low stock alert | ✅ | ⚠️ | PARTIAL (no notification) |
| Stock adjustment | ✅ | ✅ | DONE |
| Initial stock import | ✅ | ⚠️ | PARTIAL (manual only) |
| Multi-warehouse support | ✅ | ❌ | NOT DONE |

---

## 💰 Finance/Profit (การเงิน/กำไร)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| Revenue summary | ✅ | ✅ | DONE |
| Profit calculation | ✅ | ✅ | DONE |
| Platform fee breakdown | ✅ | ✅ | DONE |
| Finance sync from platforms | ✅ | ✅ | DONE |
| Export finance report | ✅ | ✅ | DONE |
| Order-level profit | ✅ | ✅ | DONE |
| SKU-level profit | ✅ | ✅ | DONE |
| COD reconciliation | ✅ | ⚠️ | PARTIAL |

---

## 🔄 Sync & Integration

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| TikTok Shop integration | ✅ | ✅ | DONE |
| Shopee integration | ✅ | ✅ | DONE |
| Lazada integration | ✅ | ✅ | DONE |
| Auto sync orders | ✅ | ✅ | DONE |
| Webhook real-time updates | ✅ | ✅ | DONE |
| Manual sync trigger | ✅ | ✅ | DONE |
| Token auto-refresh | ✅ | ✅ | DONE |

---

## 📋 Reports (รายงาน)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| Daily outbound report | ✅ | ✅ | DONE |
| Sales summary | ✅ | ✅ | DONE |
| Platform comparison | ✅ | ✅ | DONE |
| Trend charts | ✅ | ✅ | DONE |
| Export to Excel | ✅ | ✅ | DONE |

---

## 🔙 Returns (การคืนสินค้า)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| View return requests | ✅ | ✅ | DONE |
| Return status tracking | ✅ | ✅ | DONE |
| Auto update stock on return | ✅ | ✅ | DONE |
| Return reason analysis | ✅ | ⚠️ | PARTIAL |

---

## 🧾 Invoice (ใบกำกับภาษี)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| Request tax invoice | ✅ | ✅ | DONE |
| Auto-detect invoice request | ✅ | ✅ | DONE |
| Invoice profile management | ✅ | ✅ | DONE |

---

## 👤 User Management

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| Multi-user support | ✅ | ✅ | DONE |
| Role-based access | ✅ | ✅ | DONE |
| Audit log | ✅ | ⚠️ | PARTIAL |

---

## 📱 Promotions (โปรโมชั่น)

| Feature | BigSeller | WeOrder | Status |
|---------|-----------|---------|--------|
| View promotions | ✅ | ✅ | DONE |
| Promotion calculator | ✅ | ✅ | DONE |

---

## Summary

| Category | Done | Partial | Not Done |
|----------|------|---------|----------|
| Order Management | 8 | 0 | 0 |
| Packing Workflow | 6 | 0 | 0 |
| Label Printing | 6 | 0 | 0 |
| Stock/Inventory | 6 | 2 | 1 |
| Finance/Profit | 7 | 1 | 0 |
| Sync & Integration | 7 | 0 | 0 |
| Reports | 5 | 0 | 0 |
| Returns | 3 | 1 | 0 |
| Invoice | 3 | 0 | 0 |
| User Management | 2 | 1 | 0 |
| Promotions | 2 | 0 | 0 |
| **TOTAL** | **55** | **5** | **1** |

### ความครบถ้วน: **90%** (55/61 features)

---

## 🔴 สิ่งที่ต้องทำเพิ่ม

1. **Multi-warehouse support** ❌ - ยังไม่มี
2. **Low stock notification** ⚠️ - มี alert แต่ไม่มี push notification
3. **Initial stock import (Excel)** ⚠️ - ต้อง manual
4. **COD reconciliation** ⚠️ - ยังไม่ละเอียด
5. **Return reason analysis** ⚠️ - ข้อมูลไม่ครบ
6. **Audit log** ⚠️ - มีบางส่วน
