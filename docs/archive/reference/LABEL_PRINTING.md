# Label Printing Integration - Nelko PM230

## Hardware Selection

**Printer**: Nelko PM230 Portable Mini Thermal Printer
**Purchase Date**: November 2025
**Purpose**: Print QR code labels for filament spool tracking

## Printer Specifications

### Connectivity
- **Primary**: Bluetooth Low Energy (BLE)
- **Secondary**: USB (for Mac connectivity)
- **Mobile App**: Nelko app (iOS/Android)
- **Range**: Standard BLE range (~10m)

### Paper Specifications
- **Type**: Thermal paper (no ink required)
- **Width**: 2 inches (50-57mm typical for label printers)
- **Label Format**: Adhesive-backed thermal labels
- **Suitable for**: QR codes, text, simple graphics

### Technical Capabilities
- Portable, battery-powered
- Bluetooth connection to mobile devices
- USB connection to computers
- Template-based printing via Nelko app
- AI Printing, OCR, Scan, Print Docs functions

## Integration Approach

### Challenge: No Official SDK/API

The Nelko PM230 does not have publicly available:
- Software Development Kit (SDK)
- API documentation
- Developer resources
- Third-party integration guides

**Status**: Consumer-focused device with proprietary app

### Proposed Solutions (3 Options)

#### Option 1: Bluetooth Low Energy (BLE) Protocol - **RECOMMENDED**

**Description**: Reverse engineer or discover the BLE communication protocol

**Technology Stack**:
- **Python Library**: Bleak (cross-platform BLE library)
- **macOS Compatibility**: ✅ Excellent (uses CoreBluetooth)
- **Backend Integration**: Python service for label generation
- **Protocol**: Likely ESC/POS or custom thermal printer commands

**Advantages**:
- Direct control from backend
- Automated label printing
- No manual intervention
- Cross-platform (macOS, Linux, Windows)

**Disadvantages**:
- Requires protocol reverse engineering
- No official documentation
- May need BLE packet sniffing

**Implementation Path**:
1. Research similar thermal printers (Phomemo M02S, Cat Printers)
2. Use Bleak library to discover BLE services/characteristics
3. Analyze Nelko app BLE communication (Wireshark, nRF Connect)
4. Implement Python service using Bleak + ESC/POS commands
5. Create FastAPI endpoint for label printing

**Reference Projects**:
- [phomemo_m02s](https://github.com/theacodes/phomemo_m02s) - Python library for Phomemo thermal printer
- [Cat-Printer](https://github.com/NaitLee/Cat-Printer) - Bleak-based thermal printer support
- [WerWolv's Cat Printer Blog](https://werwolv.net/blog/cat_printer) - BLE protocol reverse engineering

#### Option 2: Native Printing via CUPS (macOS)

**Description**: Use Mac's native printing system

**Technology Stack**:
- **Driver**: Nelko-provided Mac driver (if available)
- **System**: CUPS (Common Unix Printing System)
- **Python**: `python-cups` library
- **Format**: PDF or image generation → system print

**Advantages**:
- Uses official driver (if available)
- Standard printing workflow
- No reverse engineering

**Disadvantages**:
- Requires driver installation
- Less direct control
- May not support advanced features
- Requires Mac to be near printer

**Implementation Path**:
1. Download Nelko Mac driver from nelkoprint.com
2. Install printer via System Settings
3. Generate QR code labels as PDFs
4. Use python-cups to send to printer
5. Create FastAPI endpoint

#### Option 3: Hybrid Approach - Mobile PWA + Web Bluetooth

**Description**: Use Progressive Web App with Web Bluetooth API

**Technology Stack**:
- **Frontend**: Web Bluetooth API (Chrome/Edge)
- **PWA**: Service Worker for offline support
- **Backend**: Generate label data, frontend sends to printer
- **Protocol**: Direct BLE communication from browser

**Advantages**:
- No backend printer connection needed
- Works from mobile devices
- Native PWA experience
- Uses existing Web Bluetooth standards

**Disadvantages**:
- Limited browser support (Chrome, Edge on desktop)
- User must initiate connection
- Less automated
- Security restrictions

**Implementation Path**:
1. Implement Web Bluetooth in React frontend
2. Backend generates QR code + label data (JSON)
3. Frontend formats as thermal printer commands
4. User clicks "Print" to send via Web Bluetooth
5. PWA installable for better UX

## Recommended Implementation: Option 1 (BLE with Bleak)

### Phase 6 Integration Plan

**Goal**: Print adhesive labels with QR codes for each filament spool

**Label Content**:
```
┌────────────────────┐
│   [QR CODE]        │
│                    │
│  FIL-001           │
│  PLA - Kingroon    │
│  Black (Basic)     │
│  1000g             │
└────────────────────┘
```

**Workflow**:
1. User creates/edits spool in web UI
2. Backend generates QR code (points to batchivo.app/spool/FIL-001)
3. Backend creates thermal printer image (QR + text)
4. Backend sends BLE commands to Nelko PM230
5. Printer outputs adhesive label
6. User sticks label to spool

### QR Code URL Structure

**Format**: `https://batchivo.app/spool/update/{spool_id}`

**Behavior**:
- Scan QR code with phone camera
- Opens Batchivo PWA to spool detail page
- Quick actions: Update weight, mark as empty, view usage
- Optimized for mobile quick updates

### Database Schema Additions

```sql
-- Add QR code tracking to spools table
ALTER TABLE spools ADD COLUMN qr_code_url VARCHAR(255);
ALTER TABLE spools ADD COLUMN qr_code_image_path VARCHAR(512);
ALTER TABLE spools ADD COLUMN label_printed_at TIMESTAMPTZ;
ALTER TABLE spools ADD COLUMN label_print_count INTEGER DEFAULT 0;
```

### Backend Implementation

**New Service**: `app/services/label_printing.py`

```python
from bleak import BleakScanner, BleakClient
import qrcode
from PIL import Image, ImageDraw, ImageFont

class NelkoPM230Service:
    """Service for controlling Nelko PM230 thermal printer via BLE"""

    DEVICE_NAME = "PM230"  # May need adjustment

    async def discover_printer(self):
        """Scan for Nelko PM230 via BLE"""
        devices = await BleakScanner.discover()
        for device in devices:
            if self.DEVICE_NAME in device.name:
                return device.address
        return None

    async def print_label(self, spool_data: dict):
        """Generate and print spool label"""
        # 1. Generate QR code
        qr_image = self._generate_qr_code(spool_data["spool_id"])

        # 2. Create label image (QR + text)
        label_image = self._create_label_image(spool_data, qr_image)

        # 3. Convert to thermal printer format
        thermal_data = self._convert_to_thermal(label_image)

        # 4. Send via BLE
        await self._send_to_printer(thermal_data)

    def _generate_qr_code(self, spool_id: str) -> Image:
        """Generate QR code for spool URL"""
        url = f"https://batchivo.app/spool/update/{spool_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

    def _create_label_image(self, spool_data: dict, qr_image: Image) -> Image:
        """Combine QR code + text into printable label"""
        # Implementation: PIL to create label layout
        pass

    def _convert_to_thermal(self, image: Image) -> bytes:
        """Convert PIL image to ESC/POS thermal commands"""
        # Implementation: Convert to monochrome, generate printer commands
        pass

    async def _send_to_printer(self, data: bytes):
        """Send data to printer via BLE"""
        address = await self.discover_printer()
        if not address:
            raise Exception("Nelko PM230 printer not found")

        async with BleakClient(address) as client:
            # Discover print characteristic (UUID to be determined)
            # await client.write_gatt_char(UUID, data)
            pass
```

**New API Endpoint**: `app/api/v1/labels.py`

```python
@router.post("/spools/{spool_id}/print-label")
async def print_spool_label(
    spool_id: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    printer_service: NelkoPM230Service = Depends()
):
    """Print QR code label for a spool"""

    # Fetch spool
    spool = await get_spool_or_404(db, spool_id, tenant.id)

    # Generate label data
    label_data = {
        "spool_id": spool.spool_id,
        "material": spool.material_type_code,
        "brand": spool.brand,
        "color": spool.color,
        "weight": f"{spool.initial_weight}g"
    }

    # Print via BLE
    await printer_service.print_label(label_data)

    # Update spool record
    spool.label_printed_at = datetime.utcnow()
    spool.label_print_count += 1
    await db.commit()

    return {"status": "success", "message": "Label printed"}
```

### Frontend Implementation

**New Component**: `src/components/labels/PrintLabelButton.tsx`

```typescript
export function PrintLabelButton({ spoolId }: { spoolId: string }) {
  const printMutation = useMutation({
    mutationFn: () => labelsApi.printLabel(spoolId),
    onSuccess: () => {
      toast.success('Label printed successfully')
    },
    onError: (error) => {
      toast.error('Failed to print label: ' + error.message)
    }
  })

  return (
    <Button onClick={() => printMutation.mutate()} disabled={printMutation.isPending}>
      {printMutation.isPending ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Printing...
        </>
      ) : (
        <>
          <Printer className="mr-2 h-4 w-4" />
          Print Label
        </>
      )}
    </Button>
  )
}
```

### Python Dependencies

```toml
# Add to backend/pyproject.toml
[tool.poetry.dependencies]
bleak = "^0.21.1"                # BLE communication
qrcode = {extras = ["pil"], version = "^7.4.2"}  # QR code generation
Pillow = "^10.1.0"               # Image processing
python-escpos = "^3.0"           # ESC/POS command generation (optional)
```

## Research & Development Tasks

### Phase 6.0: Discovery & Research (Before Implementation)

- [ ] Purchase Nelko PM230 printer (DONE - Nov 2025)
- [ ] Download and install Nelko app on iPhone/Mac
- [ ] Test basic printing via Nelko app
- [ ] Use nRF Connect app to discover BLE services/characteristics
- [ ] Analyze BLE communication with Wireshark or similar
- [ ] Research ESC/POS command set for thermal printers
- [ ] Test Bleak library connection to PM230
- [ ] Prototype simple "Hello World" print via Python

### Phase 6.1: Backend Label Generation

- [ ] Implement QR code generation service
- [ ] Create label layout engine (PIL-based)
- [ ] Add label printing columns to database
- [ ] Implement Bleak BLE printer service
- [ ] Discover PM230 BLE protocol
- [ ] Create thermal printer command converter
- [ ] Build API endpoint for label printing
- [ ] Add print queue for batch printing
- [ ] Implement error handling & retry logic

### Phase 6.2: Frontend Integration

- [ ] Add "Print Label" button to spool detail page
- [ ] Create bulk print dialog (print multiple labels)
- [ ] Show label preview before printing
- [ ] Display printer status (connected/disconnected)
- [ ] Add label history (reprints)
- [ ] Implement label templates (different sizes)

### Phase 6.3: Mobile QR Scanning

- [ ] Implement PWA camera access
- [ ] Create QR code scanner component
- [ ] Build mobile-optimized update workflow
- [ ] Add offline support for weight updates
- [ ] Implement deep link handling
- [ ] Test on iOS Safari (PWA limitations)

## Alternative: If BLE Reverse Engineering Fails

If Nelko PM230 protocol proves too difficult:

**Fallback Plan A**: Use standard ESC/POS printer
- Purchase Phomemo M02S (documented Python library)
- Or similar thermal printer with open protocol

**Fallback Plan B**: Use mobile app workflow
- Generate QR codes in web UI
- User downloads QR image
- User prints via Nelko app manually
- Still functional, just less automated

**Fallback Plan C**: Generic label printer
- Use Brother QL-820NWB or Dymo LabelWriter
- Standard driver support on macOS
- Print via CUPS

## Testing Checklist

Before Phase 6 deployment:

- [ ] BLE connection stability (multiple prints)
- [ ] QR code scannability (various phone cameras)
- [ ] Label adhesion quality
- [ ] Print quality (darkness, clarity)
- [ ] Battery life impact (BLE drain)
- [ ] Error handling (printer offline, out of paper)
- [ ] Multi-tenant isolation (correct labels per tenant)
- [ ] Print queue performance (10+ labels)

## Future Enhancements

- **Batch printing**: Print labels for all new spools
- **Auto-print on creation**: Option to print immediately after adding spool
- **Custom label templates**: User-defined layouts
- **NFC tags**: Alternative to QR codes (tap-to-update)
- **Voice commands**: "Alexa, print label for FIL-001"
- **Printer status dashboard**: Paper level, battery, connection

---

**Document Status**: Research complete, ready for Phase 6 implementation
**Last Updated**: 2025-11-02
**Owner**: Jonathan
**Priority**: Phase 6 (after core inventory, products, pricing, sales, reorder)
