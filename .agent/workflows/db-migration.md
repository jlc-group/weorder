---
description: How to safely run database migrations
---

# Database Migration Workflow

// turbo-all

## ก่อน Migration ทุกครั้ง

1. **Backup ก่อนเสมอ**
   ```bash
   # Backup current schema
   pg_dump -h $DB_HOST -U weorder_user -d weorder_db --schema-only > backup_schema_$(date +%Y%m%d_%H%M%S).sql
   
   # Backup data (optional, for critical migrations)
   pg_dump -h $DB_HOST -U weorder_user -d weorder_db > backup_full_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **ตรวจสอบ migration script ก่อนรัน**
   - อ่าน SQL/Alembic script ให้เข้าใจ
   - ระบุ tables ที่จะถูก ALTER/DROP
   - ถามผู้ใช้ก่อนถ้ามี DROP หรือ TRUNCATE

## การรัน Migration

```bash
# Alembic (ถ้าใช้)
alembic upgrade head

# หรือ raw SQL
psql -h $DB_HOST -U weorder_user -d weorder_db -f migration.sql
```

## หลัง Migration

1. **Verify schema**
   ```bash
   psql -h $DB_HOST -U weorder_user -d weorder_db -c "\\dt"
   ```

2. **Test API endpoints ที่เกี่ยวข้อง**
   ```bash
   curl -s http://localhost:9203/api/sync/status
   ```

3. **Restart backend ถ้าจำเป็น**
   ```bash
   pkill -f "uvicorn.*9203"
   sleep 2
   nohup .venv/bin/uvicorn main:app --port 9203 > /tmp/weorder_backend.log 2>&1 &
   ```

## ⚠️ ห้ามทำ

- ❌ รัน migration โดยไม่ backup
- ❌ DROP table โดยไม่ถามก่อน
- ❌ ALTER column type ที่มี data เยอะ โดยไม่ประเมิน downtime
