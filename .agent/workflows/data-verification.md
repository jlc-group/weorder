---
description: Rules for thorough verification before claiming completion
---

# Data Verification Rules

Before saying "เจอแล้ว", "แก้แล้ว", or "เสร็จแล้ว" - MUST verify:

## 1. Pre-Claim Checklist

- [ ] **Actually tested** the fix, not just wrote code
- [ ] **Checked logs** for errors after change
- [ ] **Verified data** in DB matches expectation
- [ ] **Read existing config** before asking user

## 2. Sync Issues - Check These First:

```bash
# Check sync status
curl -s http://localhost:9202/api/sync/status

# Check webhook logs
PGPASSWORD='sZ3vlr2tzjz5x#T8' psql -h 192.168.0.41 -U weorder_user -d weorder_db -c "SELECT platform, COUNT(*), MAX(received_at), COUNT(*) FILTER (WHERE processed = false) as unprocessed FROM webhook_log GROUP BY platform;"

# Check order counts
PGPASSWORD='sZ3vlr2tzjz5x#T8' psql -h 192.168.0.41 -U weorder_user -d weorder_db -c "SELECT channel_code, status_raw, COUNT(*) FROM order_header GROUP BY channel_code, status_raw ORDER BY channel_code, COUNT(*) DESC;"
```

## 3. Before Claiming "Fixed":

1. **Run the actual test** - don't just look at code
2. **Compare numbers** - DB count vs platform count
3. **Check webhook processing** - are they actually being processed?
4. **Read existing configurations** - don't ask user what's already there

## 4. If Unsure:

- Say "ผมไม่แน่ใจ ให้ตรวจสอบก่อน"
- Don't say "เจอแล้ว" until actually verified
- Don't blame API/platform without evidence

## 5. After Every Change:

```bash
# Restart backend
pkill -f "uvicorn.*9202"
sleep 2
nohup .venv/bin/uvicorn main:app --port 9202 > /tmp/weorder_backend.log 2>&1 &

# Verify it's running
sleep 5 && curl -s http://localhost:9202/api/sync/status
```
