# 🚀 WeOrder - คู่มือย้ายเครื่อง & Setup ใหม่

## 📋 ก่อนย้าย (ทำในเครื่องเก่า)

### 1. Git Push ทุกอย่าง
```bash
cd ~/Documents/Weproject/GitHub/App/weorder
git add -A
git commit -m "Pre-migration commit"
git push
```

### 2. Copy ไฟล์ที่สำคัญ (ไม่อยู่ใน Git)
```bash
# Copy .env ไปที่ปลอดภัย
cp .env ~/Desktop/weorder_backup.env
```

---

## 🖥️ ในเครื่องใหม่

### Step 1: Clone Project
```bash
cd ~/Documents/Weproject/GitHub/App  # หรือ path ที่ต้องการ
git clone https://github.com/jlc-group/weorder.git
cd weorder
```

### Step 2: Setup Backend (Python)
```bash
# สร้าง virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# หรือ .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Setup Frontend (Node.js)
```bash
cd frontend
npm install
cd ..
```

### Step 4: Copy .env
```bash
# Copy .env จากที่ backup ไว้
cp ~/Desktop/weorder_backup.env .env
```

### Step 5: Setup Global Rules (สำคัญมาก!)
```bash
# สร้างโฟลเดอร์ถ้ายังไม่มี
mkdir -p ~/.gemini

# Copy global rules จาก backup ใน repo
cp .agent/GEMINI_GLOBAL_BACKUP.md ~/.gemini/GEMINI.md
```

### Step 6: รัน Backend
```bash
source venv/bin/activate
python -m uvicorn main:app --port 9203 --host 0.0.0.0
```

### Step 7: รัน Frontend (terminal ใหม่)
```bash
cd frontend
npm run dev
```

---

## ✅ ตรวจสอบว่าทำงานได้

1. **Backend:** http://localhost:9203/api/health
2. **Frontend:** http://localhost:5173
3. **Database:** ต้องเข้าถึง 192.168.0.41 ได้ (อยู่ในเครือข่ายเดียวกัน)

---

## 📁 ไฟล์สำคัญที่ต้องรู้

| ไฟล์ | คำอธิบาย |
|------|----------|
| `.env` | Config ทั้งหมด (database, API keys) |
| `.agent/workflows/mandatory-rules.md` | กฎการทำงานสำหรับโปรเจคนี้ |
| `.agent/error_log.md` | ประวัติข้อผิดพลาด |
| `.agent/skills/weorder-agent/SKILL.md` | คำอธิบาย WeOrder project |
| `.agent/GEMINI_GLOBAL_BACKUP.md` | Backup ของ global rules |

---

## ⚠️ Lazada IP Whitelist

ถ้าย้ายไป IP ใหม่ ต้องเพิ่ม IP ใน Lazada Open Platform:
1. ไปที่ https://open.lazada.com/apps/
2. เลือก App
3. ไปที่ Settings > IP Whitelist
4. เพิ่ม IP ใหม่

---

## 🔧 คำสั่งที่ใช้บ่อย

```bash
# Start Backend
./venv/bin/python -m uvicorn main:app --port 9203 --host 0.0.0.0

# Start Frontend
cd frontend && npm run dev

# Sync Orders จาก Platforms
curl -X POST http://localhost:9203/api/sync/start

# ดู Webhook Status
curl http://localhost:9203/api/webhooks/status

# Reprocess Pending Webhooks
./venv/bin/python scripts/reprocess_webhooks.py 100
```

---

## 📞 ติดต่อ Database

```
Host:     192.168.0.41
Port:     5432
Database: weorder_db
User:     weorder_user
Password: (ดูใน .env)
```
