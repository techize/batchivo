# Nozzly Quick Start Guide

## Current Status

✅ **Completed Backend Components:**
- Production Run models (ProductionRun, ProductionRunItem, ProductionRunMaterial)
- Production Run Pydantic schemas with validation
- Complete CRUD API endpoints for production runs
- Inventory deduction service logic integrated
- Database migrations prepared
- Multi-tenant support with RLS policies

✅ **Completed Frontend Components:**
- Product management UI
- Spool inventory management UI
- Core UI component library (shadcn/ui)

⏳ **In Progress:**
- Production run frontend UI components

## Prerequisites

Before running the application:

1. **Python Environment** (backend):
   - Python 3.11+
   - Poetry package manager: `curl -sSL https://install.python-poetry.org | python3 -`

2. **Node.js Environment** (frontend):
   - Node.js 20+
   - npm or pnpm

3. **Database**:
   - SQLite (for local development)
   - OR PostgreSQL 16+ (for production features like RLS)

## Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install dependencies with Poetry
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

### Verify Backend is Running

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Verify Frontend is Running

Open browser to: `http://localhost:5173`

## Testing Production Run Endpoints

### 1. Create a Production Run

```bash
curl -X POST 'http://localhost:8000/api/v1/production-runs' \
  -H 'Content-Type: application/json' \
  -d '{
    "started_at": "2025-01-13T10:00:00Z",
    "estimated_print_time_hours": 4.5,
    "estimated_total_filament_grams": 150.0,
    "printer_name": "Bambu P1S",
    "status": "in_progress"
  }'
```

### 2. List Production Runs

```bash
curl 'http://localhost:8000/api/v1/production-runs?skip=0&limit=10'
```

### 3. Get Production Run Details

```bash
# Replace {run_id} with actual UUID from create response
curl 'http://localhost:8000/api/v1/production-runs/{run_id}'
```

### 4. Add Item to Production Run

```bash
curl -X POST 'http://localhost:8000/api/v1/production-runs/{run_id}/items' \
  -H 'Content-Type: application/json' \
  -d '{
    "product_id": "{product_uuid}",
    "quantity": 5,
    "estimated_material_cost": 3.50,
    "estimated_total_cost": 5.00
  }'
```

### 5. Add Material/Spool to Production Run

```bash
curl -X POST 'http://localhost:8000/api/v1/production-runs/{run_id}/materials' \
  -H 'Content-Type: application/json' \
  -d '{
    "spool_id": "{spool_uuid}",
    "estimated_weight_grams": 150.0,
    "estimated_purge_grams": 5.0,
    "cost_per_gram": 0.023
  }'
```

### 6. Update Material with Actual Usage (Spool Weighing)

```bash
curl -X PATCH 'http://localhost:8000/api/v1/production-runs/{run_id}/materials/{material_id}' \
  -H 'Content-Type: application/json' \
  -d '{
    "spool_weight_before_grams": 850.0,
    "spool_weight_after_grams": 695.0
  }'
```

### 7. Complete Production Run (Deducts Inventory)

```bash
# This will:
# - Validate all materials have actual usage recorded
# - Deduct inventory from spools
# - Mark run as completed
# - Calculate duration
curl -X POST 'http://localhost:8000/api/v1/production-runs/{run_id}/complete'
```

### 8. Update Production Run Status

```bash
curl -X PATCH 'http://localhost:8000/api/v1/production-runs/{run_id}' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "completed",
    "quality_rating": 5,
    "quality_notes": "Perfect print quality"
  }'
```

## API Endpoints Summary

### Production Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/production-runs` | Create new production run |
| GET | `/api/v1/production-runs` | List production runs (with filters) |
| GET | `/api/v1/production-runs/{id}` | Get production run details |
| PATCH | `/api/v1/production-runs/{id}` | Update production run |
| DELETE | `/api/v1/production-runs/{id}` | Delete production run |
| POST | `/api/v1/production-runs/{id}/complete` | Complete run & deduct inventory |

### Production Run Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/production-runs/{id}/items` | Add item to run |
| PATCH | `/api/v1/production-runs/{id}/items/{item_id}` | Update item |
| DELETE | `/api/v1/production-runs/{id}/items/{item_id}` | Remove item |

### Production Run Materials

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/production-runs/{id}/materials` | Add material/spool to run |
| PATCH | `/api/v1/production-runs/{id}/materials/{material_id}` | Update material (record usage) |
| DELETE | `/api/v1/production-runs/{id}/materials/{material_id}` | Remove material |

## Database Schema

### production_runs
- Tracks overall production run (print job)
- Supports multi-product beds
- Tracks estimated vs actual usage for variance analysis
- Quality tracking and reprint management

### production_run_items
- Links products to production runs
- Tracks quantity printed (successful/failed)
- Captures cost estimates at time of creation

### production_run_materials
- Links spools to production runs
- Supports before/after spool weighing
- Calculates actual usage and variance
- Tracks cost per gram for accurate costing

## Workflow Example

### Complete Print Job Flow:

1. **Start Production Run**
   - Create run with estimated time and filament
   - Add products to print
   - Add spools to use

2. **Weigh Spools Before Print**
   - Update materials with `spool_weight_before_grams`

3. **Print Completes**
   - Weigh spools after print
   - Update materials with `spool_weight_after_grams`
   - System calculates actual usage automatically

4. **Update Item Quantities**
   - Mark successful/failed quantities for each product

5. **Complete Production Run**
   - Call `/complete` endpoint
   - System validates all materials have usage recorded
   - Automatically deducts from spool inventory
   - Marks run as completed

6. **Review Results**
   - View variance analysis (estimated vs actual)
   - See updated spool inventory levels
   - Review cost accuracy

## Next Steps

### Immediate (Today):
- [ ] Run backend and verify API endpoints work
- [ ] Build frontend production run UI components
- [ ] Test complete workflow end-to-end

### Near-term:
- [ ] Add authentication/authorization
- [ ] Deploy to k3s cluster
- [ ] Configure Cloudflare Tunnel
- [ ] Set up observability (Grafana, Tempo, Loki)

### Future:
- [ ] Mobile app for spool weighing
- [ ] QR code scanner integration
- [ ] Printer integration (OctoPrint/Bambu)
- [ ] .gcode parser for automatic estimates
- [ ] Advanced analytics and reporting

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.11+

# Reinstall dependencies
cd backend
poetry install --no-cache

# Check for migration issues
poetry run alembic current
poetry run alembic history
```

### Database migration errors

```bash
# Reset database (CAUTION: deletes all data)
rm backend/nozzly.db
poetry run alembic upgrade head
```

### Frontend build errors

```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### API returns 422 validation errors

- Check request body matches schema in API docs
- Ensure all required fields are provided
- Verify UUID formats are correct
- Check numeric values are within allowed ranges

## Resources

- **API Documentation**: http://localhost:8000/docs (when backend running)
- **Database Schema**: `docs/DATABASE_SCHEMA.md`
- **Implementation Phases**: `docs/IMPLEMENTATION_PHASES.md`
- **Claude.md (Agent Context)**: `CLAUDE.md`

---

**Last Updated**: 2025-01-13
**Status**: Backend API Complete, Frontend UI Pending
