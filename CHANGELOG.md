## [4.1.0] - 2026-03-02

### Added
- **智能补货建议引擎** (`/api/v1/restock`)
  - 基于销售趋势、库存周转率、供应商交期自动生成补货建议
  - 计算日均销量、补货点、安全库存、经济订货量(EOQ)
  - 四级优先级系统：紧急/高/中/低
  - 库存可用天数预测
  - 补货成本汇总报告
  - 支持单产品分析和批量建议
  - 紧急补货快速查询接口

### Endpoints
- `GET /api/v1/restock/recommendations` - 获取补货建议列表（支持优先级过滤）
- `GET /api/v1/restock/recommendations/{product_id}` - 单产品补货分析
- `GET /api/v1/restock/urgent` - 紧急补货建议（库存<7天）
- `GET /api/v1/restock/summary` - 补货汇总报告

### Technical
- 新增 `RestockAdvisor` 服务类
- 新增 `RestockRecommendation` 和 `RestockPriority` 数据模型
- 完整的单元测试覆盖（15个测试用例）

# Changelog

## [4.0.0] — 2026-02-28

### Added
- **Warehouse Management** — Full warehouse CRUD, multi-warehouse stock tracking, stock transfers (draft→approved→in_transit→received lifecycle), stock adjustments (damage/return/audit/correction/write_off), inventory summary, low-stock alerts
  - Models: `Warehouse`, `StockTransfer`, `StockAdjustment`
  - Service: `WarehouseManager` with transfer lifecycle, stock validation, adjustment history
  - API: 15 endpoints under `/api/v1/warehouse/`
- **Returns & Refunds** — Complete return lifecycle management (requested→approved→item_received→refunded→closed), QC status tracking, restocking fee calculation, multiple return types (refund/replacement/exchange), 7 return reason categories
  - Models: `ReturnRequest`
  - Service: `ReturnsManager` with stats, return rate calculation
  - API: 9 endpoints under `/api/v1/returns/`
- **Customer CRM** — Unified customer records across platforms, automatic VIP tier upgrade, health score algorithm (0-100), customer interaction logging with sentiment tracking, search, tag management, order/return recording
  - Models: `Customer`, `CustomerInteraction`
  - Service: `CustomerManager` with health scoring, auto-tier-upgrade, stats
  - API: 14 endpoints under `/api/v1/customers/`
- **140+ new tests** across 3 test files (warehouse 45+, returns 40+, customer 55+)

### Fixed
- Rate limiter causing 429 errors in test suite (tokens draining across tests)
- All 303 tests now pass

### Changed
- Bumped version from 2.0.0 to 4.0.0
- API expanded from 8 to 11 router modules (38+ new endpoints)
- Total Python files: 40+
- Total lines of code: ~9,000+

## [2.0.0] — 2026-02-28

### Added
- **Shipping Service** — Cross-border shipping rate calculator with 12 carriers (4PX, YunExpress, Yanwen, Cainiao, DHL eCommerce, UBI, China Post, EMS, FedEx, UPS, SF Express, JCEX), zone-based pricing (11 zones), volumetric weight calculation, and cheapest/fastest quote comparison
- **Notification Service** — Order lifecycle notifications with pluggable channels (webhook, Telegram, email, log), event subscription, history tracking, and statistics
- **Inventory Alert Service** — Low stock/out-of-stock alerts with 3 severity levels, Economic Order Quantity (EOQ) calculator, demand-based reorder point calculation, and reorder suggestions with supplier matching
- **Reports API** — `/reports/profit` (per-product P&L), `/reports/sales-trends` (monthly trends), `/reports/inventory-health` (stock status), `/reports/overview` (comprehensive business dashboard with top products and platform breakdown)
- **Purchase Order API** — Full CRUD for purchase orders with supplier validation, receive workflow, and status management
- **Auth API** — Login endpoint with JWT, `/auth/me` for current user info
- **Rate Limiter Middleware** — Token bucket rate limiting with per-IP tracking, burst control, and Retry-After headers
- **Makefile** — `test`, `lint`, `format`, `docker`, `run`, `migrate` commands
- **75+ new tests** across 9 test files (shipping, notification, inventory_alert, profit, fx_rate, export, auth, rate_limit, config)

### Changed
- Bumped version to 2.0.0
- Updated `main.py` to register all new routers and middleware
- Expanded API from 5 to 8 router modules

## [0.1.0] — 2026-02-27

### Added
- Initial release
- Product CRUD API with search and filtering
- Order management with multi-platform support
- Inventory tracking with stock adjustment
- Supplier management
- Dashboard stats API
- JWT authentication service
- FX rate service with caching
- Data export (CSV/JSON/TSV)
- Profit calculator with cross-border cost breakdown
- Docker Compose (app + PostgreSQL + Redis)
- GitHub Actions CI (lint + test)
- Alembic migration framework
