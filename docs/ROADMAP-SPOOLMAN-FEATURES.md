# Batchivo Roadmap: Spoolman Feature Parity & Beyond

This document tracks planned features to bring Batchivo to feature parity with Spoolman, plus unique enhancements for 3D printing business management.

---

## Current State (v1.18)

### ✅ Completed
- [x] Basic spool tracking (ID, brand, color, material type)
- [x] Weight tracking (initial, current, remaining %)
- [x] Purchase tracking (price, date, supplier, batch quantity)
- [x] SpoolmanDB integration (community filament database lookup)
- [x] Color hex codes with visual swatches
- [x] Filament diameter (1.75mm / 2.85mm)
- [x] Print temperatures (extruder/bed per filament)
- [x] Special properties (translucent, glow, pattern)
- [x] Spool types (cardboard, plastic, refill, masterspool)
- [x] Density field for accurate calculations
- [x] Storage location tracking

---

## Phase 1: QR Code & Scanning (High Priority)

**Goal**: Enable quick spool identification and weight updates via QR codes

### Tasks

- [ ] **QR Code Generation**
  - Generate unique QR codes for each spool
  - Include spool ID and deep link URL
  - Support different label sizes (30x20mm, 40x30mm, custom)

- [ ] **Label Printing**
  - PDF label generation (single and batch)
  - Thermal printer support (Nelko PM230 via BLE)
  - Include: QR code, spool ID, material, color, color swatch
  - Optional: remaining weight, purchase date

- [ ] **QR Code Scanning**
  - PWA camera access for scanning
  - Deep link support: `https://batchivo.com/spool/scan/{qr_code_id}`
  - Quick actions after scan:
    - View spool details
    - Update weight
    - Mark as empty
    - Start print job (future)

- [ ] **Quick Weight Update Flow**
  - Scan → Enter weight → Save
  - Optional: gross weight mode (subtract empty spool weight)
  - History of weight updates

### Technical Notes
- Use `qrcode` Python library for generation
- Consider `html2canvas` or `jspdf` for client-side PDF generation
- BLE integration via Web Bluetooth API or native app

---

## Phase 2: Printer Integrations (Medium Priority)

**Goal**: Automatic filament usage tracking from print jobs

### OctoPrint Integration
- [ ] Plugin or direct API integration
- [ ] Track active spool per printer
- [ ] Auto-deduct filament on print completion
- [ ] Sync print job history

### Moonraker/Klipper Integration
- [ ] Moonraker API client
- [ ] Websocket connection for real-time updates
- [ ] Auto-deduct based on gcode filament usage

### Bambu Connect Integration
- [ ] Bambu Lab printer API
- [ ] AMS (Automatic Material System) support
- [ ] Multi-spool tracking per printer

### Generic Integration
- [ ] Webhook endpoint for external systems
- [ ] REST API for third-party integrations
- [ ] Spoolman-compatible API endpoint

---

## Phase 3: Multi-Printer Support (Medium Priority)

**Goal**: Track which printer is using which spool

### Tasks
- [ ] **Printer Management**
  - Add/edit/delete printers
  - Printer types (FDM, SLA, etc.)
  - Connection status tracking

- [ ] **Spool Assignment**
  - Assign spool to printer
  - Track current spool per printer
  - History of spool usage per printer

- [ ] **Print Queue Integration**
  - See pending prints per printer
  - Filament requirements for queue
  - Spool recommendations based on queue

---

## Phase 4: Usage Analytics (Medium Priority)

**Goal**: Understand filament consumption patterns

### Dashboard Metrics
- [ ] Daily/weekly/monthly usage trends
- [ ] Usage by material type
- [ ] Usage by color
- [ ] Usage by printer
- [ ] Cost per gram over time

### Prometheus Metrics
- [ ] Export metrics endpoint
- [ ] Grafana dashboard templates
- [ ] Alerts for low stock

### Reports
- [ ] Usage reports (PDF/CSV export)
- [ ] Cost analysis reports
- [ ] Inventory valuation reports

---

## Phase 5: Real-Time Updates (Low Priority)

**Goal**: Multi-user real-time collaboration

### Tasks
- [ ] WebSocket server for live updates
- [ ] Real-time spool weight changes
- [ ] Multi-user session awareness
- [ ] Optimistic UI updates

---

## Phase 6: External API (Low Priority)

**Goal**: Spoolman-compatible API for ecosystem integration

### Tasks
- [ ] Spoolman API compatibility layer
- [ ] Third-party tool support
- [ ] Slicer plugin compatibility (PrusaSlicer, OrcaSlicer)
- [ ] API documentation (OpenAPI spec)

---

## Future Considerations

### Mobile App
- Native iOS/Android app
- Offline capability
- Background QR scanning

### Hardware Integration
- Smart scale integration (auto weight updates)
- NFC tag support (alternative to QR)
- Filament sensor integration

### Advanced Features
- Filament drying tracking
- Print success rate per filament
- Color matching suggestions
- Multi-tenant marketplace (share filament data)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.18 | 2024-12-05 | SpoolmanDB integration, color hex, diameter, temps, special properties |
| v1.17 | 2024-12-04 | SpoolmanDB picker fix (Select value error) |
| v1.16 | 2024-12-04 | SpoolmanDB sync, database tables |
| v1.15 | 2024-12-04 | Color hex column size fix (RGBA support) |

---

## Contributing

This roadmap is subject to change based on user feedback and priorities. Features are implemented based on:
1. Personal use cases (dogfooding)
2. Community requests
3. Technical feasibility

---

*Last Updated: 2024-12-05*
