# WeOrder Development Guide

## Port Configuration (ห้ามเปลี่ยน!)

| Service | Port | หมายเหตุ |
|---------|------|----------|
| **Backend API** | `9203` | FastAPI/Uvicorn |
| **Frontend Dev** | `5173` | Vite dev server |
| **PostgreSQL** | `5432` | Database |

---

## Quick Start (Development)

### 1. เตรียม Environment

```bash
# Clone repository
git clone https://github.com/jlc-group/weorder.git
cd weorder

# Backend - สร้าง virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# หรือ .venv\Scripts\activate  # Windows

# ติดตั้ง dependencies
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. ตั้งค่า .env

```bash
cp .env.example .env
# แก้ไข .env ให้ตรงกับ config ของคุณ
```

### 3. รันโปรแกรม

**Option A: รันแยก (แนะนำ)**

```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn main:app --port 9203 --host 0.0.0.0

# Terminal 2 - Frontend
cd frontend
npm run dev
```

**Option B: รันด้วย script**

```bash
./start.sh
```

### 4. เข้าใช้งาน

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:9203
- **API Docs:** http://localhost:9203/docs

---

## Port ทำงานอย่างไร

```
┌─────────────────────────────────────────────────────────┐
│  Browser → http://localhost:5173                        │
│      │                                                   │
│      ├── /           → Vite Dev Server (React)          │
│      ├── /dashboard  → Vite Dev Server (React)          │
│      ├── /orders     → Vite Dev Server (React)          │
│      │                                                   │
│      └── /api/*      → Proxy → http://localhost:9203    │
│                              (FastAPI Backend)           │
└─────────────────────────────────────────────────────────┘
```

---

## Production Deployment

```bash
# Build frontend
cd frontend
npm run build

# ผลลัพธ์อยู่ใน frontend/dist/
# ใช้ Nginx serve static files + proxy API
```

Production flow:
1. Nginx listen port 80
2. Static files จาก `frontend/dist/`
3. `/api/*` proxy ไป `localhost:9203`

---

## ข้อห้าม (Mandatory Rules)

1. ❌ **ห้ามเปลี่ยน port 9203** - Backend ต้องใช้ port นี้เท่านั้น
2. ❌ **ห้ามแก้ไข deployment config** โดยไม่ถามก่อน:
   - `nginx.conf`
   - `ecosystem.config.cjs`
   - `app/core/config.py`
   - `frontend/vite.config.ts`
3. ✅ ใช้ `/api` เป็น base URL สำหรับ API calls
4. ✅ ใช้ `frontend/src/api/client.ts` สำหรับทุก API request

---

## Troubleshooting

### ปัญหา: Frontend มี error 500

```bash
cd frontend
rm -rf node_modules
npm install
npm run dev
```

### ปัญหา: Backend ไม่ start

```bash
# เช็ค port ว่าถูกใช้อยู่ไหม
lsof -i :9203

# Kill process ถ้าจำเป็น
pkill -f "uvicorn main:app"
```

### ปัญหา: Database connection error

- เช็ค `.env` ว่า `POSTGRES_*` ถูกต้อง
- เช็คว่า PostgreSQL กำลังรันอยู่

---

## Login ทดสอบ

- **Username:** `Chack`
- **Password:** `1234`
