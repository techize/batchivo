# MystmereForge Shop Integration PRD

Priority: High - needed in next 1-2 days

## Overview
Complete the MystmereForge shop integration to enable live e-commerce functionality. Backend API exists but needs improvements, frontend shop needs to be connected.

## Task 1: Migrate Cart Storage from In-Memory to Redis (High Priority)

### Goal
Replace in-memory cart storage with Redis for production reliability.

### Requirements
1. Create Redis cart service in `backend/app/services/cart.py`
2. Use Redis hashes for cart data with TTL (24 hours)
3. Key format: `cart:{session_id}`
4. Implement cart recovery for returning visitors
5. Add cart expiration cleanup job

### Test Strategy
Test cart persistence across server restarts. Verify TTL expiration. Load test with 100 concurrent carts.

---

## Task 2: Complete Shop Frontend Integration (High Priority)

### Goal
Connect the MystmereForge frontend to Nozzly backend API.

### Requirements
1. Configure API base URL for shop frontend
2. Implement product grid with pricing from Nozzly products
3. Wire up cart functionality (add, remove, update quantities)
4. Implement checkout flow with Square Web Payments SDK
5. Display order confirmation with order number
6. Handle payment errors gracefully

### Test Strategy
E2E test of complete purchase flow. Test with Square sandbox. Verify order appears in Nozzly admin.

---

## Task 3: Add Product Images and Categories (Medium Priority)

### Goal
Enable product images and category filtering in shop.

### Requirements
1. Add `images` JSON field to Product model (or create ProductImage table)
2. Create image upload endpoint with MinIO storage
3. Add `category` field to Product model
4. Implement category CRUD endpoints
5. Update shop API to return images and categories
6. Create category management UI in Nozzly admin

### Test Strategy
Test image upload and retrieval. Verify category filtering works.

---

## Task 4: Implement Order Management Dashboard (High Priority)

### Goal
Create order management interface in Nozzly admin for processing MystmereForge orders.

### Requirements
1. Create OrderList page with filters (status, date, channel)
2. Create OrderDetail page showing items, shipping, payment
3. Implement status transitions: pending → processing → shipped → delivered
4. Add tracking number field and update endpoint
5. Send email notifications on status change (integrate with email service)
6. Add "fulfill order" workflow (deduct inventory, mark shipped)

### Test Strategy
Test order creation from shop checkout. Verify status updates. Test inventory deduction on fulfillment.

---

## Task 5: Add Inventory Sync with Shop (Medium Priority)

### Goal
Automatically update product availability based on inventory levels.

### Requirements
1. Add `units_in_stock` field sync to shop product response
2. Hide out-of-stock products or show "Out of Stock" badge
3. Prevent checkout if product becomes unavailable
4. Create low stock alerts for shop products
5. Optional: Reserve stock during checkout (with timeout)

### Test Strategy
Test stock display updates. Test checkout prevention for out-of-stock items.
