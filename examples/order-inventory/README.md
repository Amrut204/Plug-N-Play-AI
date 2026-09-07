# Starter Template: Order, Inventory & Warehouse Operations Assistant

Designed for e-commerce brands, logistics hubs, and operational inventory teams.

## Components Included
1. **Relational Schema (`schema.sql`)**:
   - `products` & `categories`: SKUs, pricing, costs, availability status.
   - `warehouses`: Geographic logistics nodes (East Coast, West Coast).
   - `inventory`: On-hand stock, reserved stock, reorder thresholds.
   - `customers` & `orders`: Order tracking, carriers (FedEx, UPS, USPS), loyalty tiers (`bronze`, `gold`, `vip`).
   - `order_items`: Line-item breakdown of purchased SKUs.
2. **Policy Documentation (`docs/return_shipping_policy.md`)**:
   - 30-day return eligibility and condition criteria.
   - Expedited shipping rules and order cut-off times.
   - 48-hour damaged/defective replacement policy (DOA).
3. **Pre-configured Roles & RBAC**:
   - `admin` / `manager`: Full warehouse inventory auditing, reorder threshold alerts, revenue analysis.
   - `customer`: Programmatic RLS restricting orders to `WHERE customer_id = :auth_customer_id`.

## Quickstart Testing with SQLite
```bash
sqlite3 inventory_ops.db < examples/order-inventory/schema.sql
```
Connect `sqlite:///inventory_ops.db` directly in the Agent Studio.
