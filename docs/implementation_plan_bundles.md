
# Product & Bundle Restructuring Plan

## Status: Partially Complete

### Done
- [x] Database Schema for `platform_listing` and `platform_listing_item`
- [x] API Endpoints for Listings (CRUD + Auto-Import)
- [x] Frontend Page (`/bundles`) with Layout & Tabs
- [x] Auto-Import Feature using Historical Orders
- [x] Daily Sync Script & Cronjob Setup (`run_daily_sync.sh`)

### Pending
- [ ] Edit/Update existing mappings
- [ ] Integration with Order Sync Logic (Stock Deduction)
- [ ] Frontend: Improve Product Search Modal

## 1. Database Schema (Implemented)
Models created in `app/models/mapping.py`:
- `PlatformListing`: Represents a sellable item/bundle on a platform (Shopee, Lazada, TikTok).
- `PlatformListingItem`: Links a listing to one or more Master Products with quantity.

## 2. API Endpoints (Implemented)
- `GET /api/listings/`: List all mappings
- `POST /api/listings/`: Create new mapping
- `DELETE /api/listings/{id}`: Delete mapping
- `POST /api/listings/import-from-history`: Auto-import from historical orders

## 3. Order Sync Logic (Next Step)
We need to modify `app/services/stock_service.py` or the order processing logic to use `PlatformListing` for looking up which Master Products to deduct stock from.

**Logic:**
1. When order comes in with `platform_sku`.
2. Look up `PlatformListing` where `platform` and `platform_sku` match.
3. If found, deduce stock for all `PlatformListingItem`s associated with it.
4. If NOT found, fallback to checking if `platform_sku` matches a Master Product SKU directly.
