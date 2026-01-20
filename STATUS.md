# WeOrder Status

> **Quick Status:** Running - Production ready  
> **Port:** 9203  
> **Domain:** weorder.jlcgroup.co  
> **Local URL:** http://localhost:9203

---

## Current State

- **Backend running** on port 9203
- **Frontend built** and served via FastAPI
- **Health check** at /health
- **API docs** at /docs
- **Nginx configured** for weorder.jlcgroup.co
- **Autostart** via startup-all.ps1

## Completed

- [x] Clone repository
- [x] Create folders (data, logs, run)
- [x] Install Python 3.12
- [x] Install dependencies
- [x] Update config.py to load .env from run/weorder/
- [x] Connect to database weorder_db
- [x] Create nginx config
- [x] Add to ecosystem.config.js
- [x] Add to startup-all.ps1 for autostart
- [x] Build React frontend
- [x] Frontend serving via FastAPI

## Pending (Cloudflare)

- [ ] Add DNS A record in Cloudflare for weorder.jlcgroup.co -> server public IP

## How to Access

| URL | Status |
|-----|--------|
| http://localhost:9203 | Working |
| http://192.168.0.41:9203 | Working (LAN) |
| http://weorder.jlcgroup.co | Pending Cloudflare DNS |

## Notes

- Database: `weorder_db` (PostgreSQL)
- Python: `C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe`
- Frontend: React + Vite (built to dist/)
- Cloudflare: Need to add A record pointing to server

---
*Last updated: 2026-01-13*
