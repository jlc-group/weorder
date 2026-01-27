# ๐Ÿ"ฆ WeOrder - Project Context

> **Vision:** ระบบจัดการออเดอร์แบบรวมศูนย์สำหรับ JLC Group  
> **Status:** Production (migrating to new server)  
> **Owner:** JLC Group

---

## ๐ŸŽฏ Purpose

WeOrder เป็นระบบจัดการออเดอร์จากทุกช่องทางขาย:
- **Shopee** - sync orders อัตโนมัติ
- **Lazada** - sync orders อัตโนมัติ
- **TikTok Shop** - sync orders อัตโนมัติ
- **Facebook** - manual entry
- **Walk-in** - manual entry

---

## ๐Ÿ—๏ธ Architecture

```
Frontend (React + Vite)
         ↓
Backend (FastAPI) :9203
         ↓
PostgreSQL (weorder)
         ↓
Platform APIs (Shopee, Lazada, TikTok)
```

---

## ๐Ÿ"‹ Core Features

### 1. Order Management
- รับออเดอร์จากทุก platform
- สถานะ: Pending → Picked → Packed → Shipped → Delivered

### 2. Product Master
- จัดการสินค้า, SKU mapping
- Set/Bundle management
- Platform SKU mapping

### 3. Stock Management
- Ledger-based stock tracking
- Multi-warehouse support
- Pre-pack boxes

### 4. Packing System
- Pick list generation
- Shipping labels
- Pre-pack workflow

### 5. Promotion Engine
- ของแถมหลังบ้าน
- Auto-apply promotions

### 6. Finance
- บันทึกรับชำระ
- Platform fee tracking
- Invoice generation

---

## ๐Ÿ"Œ Integration Points

| Platform | Type | Status |
|----------|------|--------|
| Shopee | API | โœ… Active |
| Lazada | API | โœ… Active |
| TikTok Shop | API | โœ… Active |
| JLC SSO | OAuth | ๐Ÿ" Pending |

---

## ๐Ÿ"‚ Folder Structure

```
apps/weorder/
├── app/              # FastAPI backend
│   ├── api/          # API endpoints
│   ├── core/         # Config, database
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── templates/    # Jinja2 templates
├── frontend/         # React frontend
├── migrations/       # Alembic (ถ้ามี)
├── main.py           # Entry point
└── requirements.txt
```

---

## ๐Ÿ"— Related Resources

- **Source:** `D:\Server\apps\weorder\`
- **Data:** `D:\Server\data\weorder\`
- **Logs:** `D:\Server\logs\weorder\`
- **Runtime:** `D:\Server\run\weorder\`
- **Domain:** https://weorder.jlcgroup.co

---
*Created: 2026-01-13*
