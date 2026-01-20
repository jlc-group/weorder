# WeOrder Deployment Guide

## สิ่งที่ต้องมีบน Production Server

- **Python 3.11+**
- **PostgreSQL 14+**
- **Nginx**
- **Node.js 18+** (สำหรับ build frontend)

---

## 1. Clone และ Setup

```bash
cd /var/www
git clone <repo-url> weorder
cd weorder

# สร้าง virtual environment
python3 -m venv .venv
source .venv/bin/activate

# ติดตั้ง dependencies
pip install -r requirements.txt
```

---

## 2. ตั้งค่า Database

```bash
# สร้าง database
sudo -u postgres createdb weorder

# แก้ไข .env ให้ตรงกับ database
cp .env.example .env
nano .env
```

**.env ที่ต้องแก้:**
```
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=weorder
POSTGRES_PORT=5432
```

---

## 3. Build Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 4. ติดตั้ง Nginx

```bash
# Copy config
sudo cp nginx.conf /etc/nginx/sites-available/weorder

# แก้ไข domain และ path ให้ถูกต้อง
sudo nano /etc/nginx/sites-available/weorder

# Enable site
sudo ln -s /etc/nginx/sites-available/weorder /etc/nginx/sites-enabled/

# Test และ reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. ติดตั้ง Backend Service

```bash
# Copy service file
sudo cp weorder.service /etc/systemd/system/

# แก้ไข path ถ้าต่างจาก /var/www/weorder
sudo nano /etc/systemd/system/weorder.service

# Enable และ start
sudo systemctl daemon-reload
sudo systemctl enable weorder
sudo systemctl start weorder

# ดู logs
sudo journalctl -u weorder -f
```

---

## 6. ทดสอบ

```bash
# เช็ค health
curl http://localhost:9203/health

# เช็คผ่าน nginx
curl http://your-domain.com/health
```

---

## Default Login

| Username | Password |
|----------|----------|
| admin    | admin123 |

---

## Files ที่สำคัญ

| File | คำอธิบาย |
|------|----------|
| `nginx.conf` | Nginx configuration |
| `weorder.service` | Systemd service |
| `.env` | Environment variables |
| `main.py` | Backend entry point |
| `frontend/dist/` | Built frontend |

---

## Troubleshooting

### 405 Method Not Allowed
- ตรวจสอบว่า backend รัน: `sudo systemctl status weorder`
- ตรวจสอบ nginx proxy: `sudo nginx -t`

### 502 Bad Gateway
- Backend ไม่ได้รัน: `sudo systemctl start weorder`
- Port ไม่ถูก: ตรวจสอบ port ใน nginx.conf และ .env

### Database Error
- ตรวจสอบ .env ว่า credentials ถูกต้อง
- PostgreSQL service รัน: `sudo systemctl status postgresql`
