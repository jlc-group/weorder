# WeOrder - Unified Order Management System

ระบบจัดการออเดอร์แบบรวมศูนย์สำหรับ JLC Group

## Features

- **Order Management** - จัดการออเดอร์จากทุกช่องทาง (Shopee, Lazada, TikTok, Facebook, Manual)
- **Product Master** - จัดการสินค้า, SKU mapping, Set/Bundle
- **Stock Management** - ระบบสต๊อกแบบ Ledger
- **Packing System** - ระบบแพ็คสินค้า, Pre-pack boxes, ใบปะหน้า
- **Promotion Engine** - ของแถมหลังบ้าน, Auto-apply promotions
- **Finance** - บันทึกรับชำระ, ติดตามสถานะการชำระเงิน

## Tech Stack

- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0
- **Templates**: Jinja2 + Bootstrap 5
- **Port**: 9202

## Project Structure

```
apps/weorder/
├── app/
│   ├── api/         # API endpoints (JSON)
│   ├── web/         # Web routes (HTML)
│   ├── core/        # Config, database
│   ├── models/      # SQLAlchemy models
│   ├── schemas/     # Pydantic schemas
│   ├── services/    # Business logic
│   ├── static/      # CSS, JS, images
│   └── templates/   # Jinja2 templates
├── migrations/      # Alembic migrations
├── main.py          # Entry point
├── requirements.txt
└── ecosystem.config.cjs
```

## Setup

1. Install dependencies:
```bash
cd D:\IISSERVER\apps\weorder
pip install -r requirements.txt
```

2. Create database:
```sql
CREATE DATABASE weorder;
```

3. Configure environment:
- Edit `D:\IISSERVER\run\weorder\.env`

4. Run the application:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 9202 --reload
```

## PM2 Deployment

```bash
cd D:\IISSERVER\apps\weorder
pm2 start ecosystem.config.cjs
pm2 save
```

## URLs

- **Local**: http://localhost:9202
- **Production**: https://weorder.jlcgroup.co
- **API Docs**: http://localhost:9202/docs
- **Health Check**: http://localhost:9202/health

## Related Folders

- Source: `D:\IISSERVER\apps\weorder\`
- Data: `D:\IISSERVER\data\weorder\`
- Logs: `D:\IISSERVER\logs\weorder\`
- Runtime: `D:\IISSERVER\run\weorder\`
