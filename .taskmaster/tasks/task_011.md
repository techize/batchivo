# Task ID: 11

**Title:** Create Analytics and Variance Endpoints

**Status:** pending

**Dependencies:** 10 ✓

**Priority:** medium

**Description:** Implement variance analysis and production analytics API endpoints

**Details:**

Add analytics endpoints to production_runs.py: GET /variance-report (variance analysis across runs with aggregations), GET /products/{id}/production-history (production history for specific product), GET /spools/{id}/production-usage (runs that used specific spool). Implement variance calculation aggregations: average variance per product, runs with highest variance, variance trends over time. Use SQLAlchemy aggregation functions (func.avg, func.sum). Add caching for expensive queries using Redis. Include OpenTelemetry metrics for variance tracking.

**Test Strategy:**

Unit tests for variance calculations, integration tests for analytics endpoints, performance tests for aggregation queries

## Subtasks

### 11.1. Implement Basic Variance Report Endpoint

**Status:** pending
**Dependencies:** None

Create GET /variance-report endpoint with SQLAlchemy aggregation functions for variance analysis across production runs

**Details:**

Implement variance-report endpoint in production_runs.py using SQLAlchemy aggregation functions (func.avg, func.sum, func.count). Calculate average variance per product, identify runs with highest variance, and show variance trends over time. Include filters for date range, product, and variance threshold. Return aggregated data with proper pagination and sorting options.

### 11.2. Create Product Production History Endpoint

**Status:** pending
**Dependencies:** 11.1

Build GET /products/{id}/production-history endpoint with performance optimization for tracking production runs per product

**Details:**

Implement production history endpoint with eager loading of related production runs, items, and materials. Include query optimization using joins and select_related. Add pagination, sorting by date, and filtering by status and date range. Return comprehensive production statistics including total runs, success rates, and average variances.

### 11.3. Implement Spool Usage Tracking Endpoint

**Status:** pending
**Dependencies:** 11.1

Create GET /spools/{id}/production-usage endpoint to track which production runs used specific spools

**Details:**

Build spool usage endpoint that returns all production runs that consumed material from a specific spool. Include actual weights used, dates, products produced, and remaining spool weight calculations. Add aggregations for total usage, average usage per run, and usage trend analysis. Optimize query performance with proper indexing.

### 11.4. Add Redis Caching and OpenTelemetry Metrics

**Status:** pending
**Dependencies:** 11.1, 11.2, 11.3

Implement Redis caching for expensive aggregation queries and add OpenTelemetry metrics for variance tracking

**Details:**

Add Redis caching layer for variance calculations and aggregation queries with configurable TTL. Implement cache invalidation on production run updates. Add OpenTelemetry metrics for variance tracking including gauges for average variance, counters for high-variance runs, and histograms for variance distribution. Include cache hit/miss metrics and query performance tracking.
