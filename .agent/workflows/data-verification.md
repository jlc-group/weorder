---
description: Rules to verify data integrity before claiming accuracy
---

# กฎการตรวจสอบความถูกต้องของข้อมูล

## หลักการสำคัญ
**ห้ามพูดว่า "ข้อมูลถูกต้อง" หรือ "ทำงานได้แล้ว" โดยไม่ได้ตรวจสอบจริง!**

## ขั้นตอนบังคับก่อนยืนยันข้อมูล

### 1. Query ข้อมูลจาก Database โดยตรง
```bash
source .venv/bin/activate && python3 -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
# YOUR QUERY HERE
db.close()
"
```

### 2. เปรียบเทียบกับ API Response
```bash
curl -s 'http://localhost:9202/api/YOUR_ENDPOINT' | jq .
```

### 3. เปรียบเทียบกับ UI Display
- ใช้ browser subagent ดู screenshot จริง
- จดตัวเลขที่แสดงใน UI
- เทียบกับตัวเลขจาก DB query

## Checklist ก่อนบอกว่าข้อมูลถูกต้อง

- [ ] Query DB โดยตรงแล้ว (ไม่ใช่ดูแค่ API)
- [ ] ดู screenshot ของ UI จริง (ไม่ใช่แค่เชื่อว่าโหลดได้)
- [ ] ตัวเลข DB = ตัวเลข API = ตัวเลข UI
- [ ] ถ้าไม่ตรงกัน ต้องหาสาเหตุก่อน

## ตัวอย่าง Query ที่ใช้บ่อย

### ตรวจสอบยอดส่งรายวัน (Daily Outbound)
```sql
SELECT 
    DATE(shipped_at AT TIME ZONE 'Asia/Bangkok') as ship_date,
    channel_code,
    COUNT(*) as order_count,
    SUM(total_amount) as total_amount
FROM order_header 
WHERE shipped_at >= 'YYYY-MM-DD 17:00:00+00'  -- วันก่อนหน้า UTC
AND shipped_at < 'YYYY-MM-DD 17:00:00+00'      -- วันปัจจุบัน UTC
AND status_normalized NOT IN ('CANCELLED', 'RETURNED')
GROUP BY DATE(shipped_at AT TIME ZONE 'Asia/Bangkok'), channel_code
ORDER BY ship_date, channel_code
```

### ตรวจสอบ Orders by Status
```sql
SELECT status_normalized, COUNT(*) 
FROM order_header 
GROUP BY status_normalized
ORDER BY COUNT(*) DESC
```

### ตรวจสอบ Timezone Issues
```sql
-- Thai timezone = UTC+7
-- ดังนั้น วันที่ 5 มกราคม Thai = 4 มกราคม 17:00 UTC ถึง 5 มกราคม 17:00 UTC
SELECT 
    shipped_at,
    shipped_at AT TIME ZONE 'Asia/Bangkok' as thai_time
FROM order_header
WHERE shipped_at IS NOT NULL
LIMIT 5
```

## Warning Signs ที่ต้องตรวจสอบเพิ่ม

1. **ตัวเลขเป็น 0** - ต้อง query DB ยืนยัน
2. **ตัวเลขสูงผิดปกติ** - อาจมี duplicate หรือ timezone ผิด
3. **Timezone mismatch** - Thai time vs UTC
4. **Missing data** - shipped_at เป็น NULL?

## สิ่งที่ห้ามทำ

- ❌ เชื่อ API response โดยไม่ query DB
- ❌ บอกว่า "ทำงานได้" แค่เพราะไม่มี error
- ❌ ข้ามขั้นตอนการ verify เพราะรีบ
- ❌ Assume ว่าข้อมูลถูกต้องถ้า UI render ได้
