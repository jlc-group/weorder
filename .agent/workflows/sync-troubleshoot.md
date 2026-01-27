---
description: Troubleshoot sync issues with TikTok/Shopee/Lazada
---

# Sync Troubleshooting Workflow

// turbo-all

## Quick Diagnosis

```bash
# 1. Check sync status
curl -s http://localhost:9203/api/sync/status | jq .

# 2. Check if backend is running
ps aux | grep "uvicorn.*9203" | grep -v grep

# 3. Check recent sync logs
tail -50 /tmp/weorder_logs/scheduler.log
```

## Common Issues

### 1. Orders Not Syncing

```bash
# Check webhook processing
curl -s "http://localhost:9203/api/webhooks/stats"

# Check platform configs
curl -s "http://localhost:9203/api/platforms/status"

# Manual trigger sync
curl -X POST "http://localhost:9203/api/sync/trigger?platform=tiktok&days=3"
```

### 2. Token Expired

```bash
# Check token status
curl -s "http://localhost:9203/api/platforms/status" | jq '.[] | {platform, token_valid, expires_at}'

# Refresh token (Shopee)
python scripts/update_shopee_tokens.py

# For TikTok - need manual re-auth via web
```

### 3. Duplicate Orders

```sql
-- Find duplicates
SELECT platform_order_id, COUNT(*) 
FROM order_header 
GROUP BY platform_order_id 
HAVING COUNT(*) > 1;

-- Check webhook logs for duplicates
SELECT payload->>'order_id', COUNT(*), array_agg(id)
FROM webhook_log 
WHERE platform = 'tiktok'
GROUP BY payload->>'order_id'
HAVING COUNT(*) > 1;
```

### 4. Finance Data Missing

```bash
# Check finance sync
curl -s "http://localhost:9203/api/finance/last-sync"

# Manual trigger finance sync
curl -X POST "http://localhost:9203/api/finance/sync?platform=shopee&days=7"
```

## Verification After Fix

1. Wait 5 minutes
2. Check sync status again
3. Compare counts: API vs Database
4. Check frontend dashboard loads

## ⚠️ ก่อนบอกว่า "แก้แล้ว"

- [ ] Verified sync actually runs
- [ ] Checked new orders appear in DB
- [ ] Frontend shows updated data
- [ ] No errors in logs
