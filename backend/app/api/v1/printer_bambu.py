"""Bambu Lab printer integration API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models import AMSSlotMapping, Printer, PrinterConnection, Spool
from app.schemas.ams_slot_mapping import (
    AMSFullStatus,
    AMSSlotListResponse,
    AMSSlotMappingCreate,
    AMSSlotMappingResponse,
    AMSSlotMappingWithSpool,
    SpoolSummaryForAMS,
)
from app.schemas.printer_connection import (
    BambuPrinterStatus,
    ConnectionType,
    PrinterConnectionCreate,
    PrinterConnectionResponse,
    PrinterConnectionStatus,
    PrinterConnectionUpdate,
)
from app.services.bambu_mqtt import (
    BambuConnectionConfig,
    get_bambu_mqtt_service,
)

router = APIRouter()


# ============================================
# Printer Connection Endpoints
# ============================================


@router.post(
    "/{printer_id}/connection",
    response_model=PrinterConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_printer_connection(
    printer_id: UUID,
    connection_data: PrinterConnectionCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterConnectionResponse:
    """
    Create or update connection configuration for a printer.

    For Bambu Lab printers:
    - connection_type: bambu_lan or bambu_cloud
    - serial_number: Found on printer screen or in Bambu Studio
    - ip_address: Printer's LAN IP address
    - access_code: LAN access code from printer settings

    Replaces any existing connection config for this printer.
    """
    # Verify printer exists and belongs to tenant
    result = await db.execute(
        select(Printer).where(
            Printer.id == printer_id,
            Printer.tenant_id == tenant.id,
        )
    )
    printer = result.scalar_one_or_none()

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Printer not found",
        )

    # Check for existing connection
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        for key, value in connection_data.model_dump(exclude_unset=True).items():
            if key == "connection_type":
                value = value.value if isinstance(value, ConnectionType) else value
            setattr(existing, key, value)
        connection = existing
    else:
        # Create new
        connection = PrinterConnection(
            tenant_id=tenant.id,
            printer_id=printer_id,
            **connection_data.model_dump(exclude_unset=True, exclude={"connection_type"}),
            connection_type=connection_data.connection_type.value,
        )
        db.add(connection)

    await db.commit()
    await db.refresh(connection)

    return PrinterConnectionResponse.model_validate(connection)


@router.get(
    "/{printer_id}/connection",
    response_model=PrinterConnectionResponse,
)
async def get_printer_connection(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterConnectionResponse:
    """Get connection configuration for a printer."""
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    return PrinterConnectionResponse.model_validate(connection)


@router.put(
    "/{printer_id}/connection",
    response_model=PrinterConnectionResponse,
)
async def update_printer_connection(
    printer_id: UUID,
    connection_data: PrinterConnectionUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterConnectionResponse:
    """Update connection configuration for a printer."""
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    for key, value in connection_data.model_dump(exclude_unset=True).items():
        if value is not None:
            if key == "connection_type":
                value = value.value if isinstance(value, ConnectionType) else value
            setattr(connection, key, value)

    await db.commit()
    await db.refresh(connection)

    return PrinterConnectionResponse.model_validate(connection)


@router.delete(
    "/{printer_id}/connection",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_printer_connection(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """Delete connection configuration and disconnect from printer."""
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    # Disconnect from MQTT if connected
    mqtt_service = get_bambu_mqtt_service()
    if mqtt_service.is_connected(printer_id):
        await mqtt_service.disconnect(printer_id)

    await db.delete(connection)
    await db.commit()


# ============================================
# MQTT Connection Control Endpoints
# ============================================


@router.post(
    "/{printer_id}/connection/connect",
    response_model=PrinterConnectionStatus,
)
async def connect_to_printer(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterConnectionStatus:
    """
    Initiate MQTT connection to a Bambu printer.

    Requires connection configuration to be set up first.
    """
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    if connection.connection_type not in ("bambu_lan", "bambu_cloud"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MQTT connection only supported for Bambu printers",
        )

    if not connection.serial_number or not connection.ip_address or not connection.access_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required connection details (serial_number, ip_address, access_code)",
        )

    # Connect via MQTT service
    mqtt_service = get_bambu_mqtt_service()
    config = BambuConnectionConfig(
        printer_id=printer_id,
        serial_number=connection.serial_number,
        ip_address=connection.ip_address,
        port=connection.port,
        access_code=connection.access_code,
    )

    success = await mqtt_service.connect(config)

    if not success:
        connection.connection_error = "Failed to initiate MQTT connection"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to printer",
        )

    connection.is_connected = True
    connection.connection_error = None
    await db.commit()
    await db.refresh(connection)

    return PrinterConnectionStatus.model_validate(connection)


@router.post(
    "/{printer_id}/connection/disconnect",
    response_model=PrinterConnectionStatus,
)
async def disconnect_from_printer(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterConnectionStatus:
    """Disconnect MQTT connection from a Bambu printer."""
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    mqtt_service = get_bambu_mqtt_service()
    await mqtt_service.disconnect(printer_id)

    connection.is_connected = False
    await db.commit()
    await db.refresh(connection)

    return PrinterConnectionStatus.model_validate(connection)


@router.get(
    "/{printer_id}/status",
    response_model=BambuPrinterStatus,
)
async def get_printer_status(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> BambuPrinterStatus:
    """
    Get live status of a connected Bambu printer.

    Includes print progress, temperatures, and error state.
    """
    # Verify printer belongs to tenant
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    mqtt_service = get_bambu_mqtt_service()
    printer_status = mqtt_service.get_printer_status(printer_id)

    if not printer_status:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Printer not connected or status unavailable",
        )

    return printer_status


# ============================================
# AMS Slot Mapping Endpoints
# ============================================


@router.get(
    "/{printer_id}/ams",
    response_model=AMSSlotListResponse,
)
async def list_ams_slots(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> AMSSlotListResponse:
    """
    List all AMS slot mappings for a printer.

    Returns all slots across all AMS units with their mapped spools.
    """
    # Get printer connection to find AMS count
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    ams_count = connection.ams_count if connection else 0

    # Get all slot mappings
    result = await db.execute(
        select(AMSSlotMapping)
        .options(selectinload(AMSSlotMapping.spool))
        .where(
            AMSSlotMapping.printer_id == printer_id,
            AMSSlotMapping.tenant_id == tenant.id,
        )
        .order_by(AMSSlotMapping.ams_id, AMSSlotMapping.tray_id)
    )
    mappings = result.scalars().all()

    # Convert to response with spool summaries
    slots = []
    for mapping in mappings:
        spool_summary = None
        if mapping.spool:
            spool_summary = SpoolSummaryForAMS(
                id=mapping.spool.id,
                spool_id=mapping.spool.spool_id,
                brand=mapping.spool.brand,
                color=mapping.spool.color,
                color_hex=mapping.spool.color_hex,
                material_type_code=mapping.spool.material_type.code
                if mapping.spool.material_type
                else None,
                current_weight=float(mapping.spool.current_weight),
                initial_weight=float(mapping.spool.initial_weight),
            )

        slot_response = AMSSlotMappingWithSpool(
            **AMSSlotMappingResponse.model_validate(mapping).model_dump(),
            spool_summary=spool_summary,
        )
        slots.append(slot_response)

    return AMSSlotListResponse(
        printer_id=printer_id,
        ams_count=ams_count,
        total_slots=ams_count * 4,
        slots=slots,
    )


@router.post(
    "/{printer_id}/ams/map",
    response_model=AMSSlotMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def map_ams_slot(
    printer_id: UUID,
    mapping_data: AMSSlotMappingCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> AMSSlotMappingResponse:
    """
    Map an AMS slot to a Nozzly spool.

    Creates or updates the mapping for the specified AMS slot.
    """
    # Verify printer exists
    result = await db.execute(
        select(Printer).where(
            Printer.id == printer_id,
            Printer.tenant_id == tenant.id,
        )
    )
    printer = result.scalar_one_or_none()

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Printer not found",
        )

    # Verify spool if provided
    if mapping_data.spool_id:
        result = await db.execute(
            select(Spool).where(
                Spool.id == mapping_data.spool_id,
                Spool.tenant_id == tenant.id,
            )
        )
        spool = result.scalar_one_or_none()

        if not spool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spool not found",
            )

    # Check for existing mapping
    result = await db.execute(
        select(AMSSlotMapping).where(
            AMSSlotMapping.printer_id == printer_id,
            AMSSlotMapping.ams_id == mapping_data.ams_id,
            AMSSlotMapping.tray_id == mapping_data.tray_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.spool_id = mapping_data.spool_id
        existing.is_auto_mapped = False
        mapping = existing
    else:
        mapping = AMSSlotMapping(
            tenant_id=tenant.id,
            printer_id=printer_id,
            ams_id=mapping_data.ams_id,
            tray_id=mapping_data.tray_id,
            spool_id=mapping_data.spool_id,
            is_auto_mapped=False,
        )
        db.add(mapping)

    await db.commit()
    await db.refresh(mapping)

    return AMSSlotMappingResponse.model_validate(mapping)


@router.delete(
    "/{printer_id}/ams/{ams_id}/{tray_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unmap_ams_slot(
    printer_id: UUID,
    ams_id: int,
    tray_id: int,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """Remove spool mapping from an AMS slot."""
    result = await db.execute(
        select(AMSSlotMapping).where(
            AMSSlotMapping.printer_id == printer_id,
            AMSSlotMapping.tenant_id == tenant.id,
            AMSSlotMapping.ams_id == ams_id,
            AMSSlotMapping.tray_id == tray_id,
        )
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AMS slot mapping not found",
        )

    mapping.spool_id = None
    mapping.is_auto_mapped = False
    await db.commit()


@router.get(
    "/{printer_id}/ams/live",
    response_model=AMSFullStatus,
)
async def get_live_ams_status(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> AMSFullStatus:
    """
    Get live AMS status from connected printer.

    Returns real-time filament data from all AMS units including
    remaining percentages, colors, and material types.
    """
    # Verify printer belongs to tenant
    result = await db.execute(
        select(PrinterConnection).where(
            PrinterConnection.printer_id == printer_id,
            PrinterConnection.tenant_id == tenant.id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connection configured for this printer",
        )

    mqtt_service = get_bambu_mqtt_service()
    state = mqtt_service.get_printer_state(printer_id)

    if not state or not state.is_online:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Printer not connected",
        )

    ams_status = mqtt_service.get_ams_status(printer_id)

    return AMSFullStatus(
        printer_id=printer_id,
        ams_units=ams_status,
        tray_now=state.tray_now if state.tray_now != 255 else None,
        last_updated_at=state.last_seen_at,
    )


@router.post(
    "/{printer_id}/ams/sync",
    response_model=AMSSlotListResponse,
)
async def sync_ams_to_inventory(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> AMSSlotListResponse:
    """
    Sync AMS remaining percentages to mapped Nozzly spools.

    Updates current_weight on mapped spools based on AMS reported
    remaining percentage and initial weight.
    """
    mqtt_service = get_bambu_mqtt_service()
    state = mqtt_service.get_printer_state(printer_id)

    if not state or not state.is_online:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Printer not connected",
        )

    ams_status = mqtt_service.get_ams_status(printer_id)

    # Get all mappings with spools
    result = await db.execute(
        select(AMSSlotMapping)
        .options(selectinload(AMSSlotMapping.spool))
        .where(
            AMSSlotMapping.printer_id == printer_id,
            AMSSlotMapping.tenant_id == tenant.id,
        )
    )
    mappings = result.scalars().all()

    # Update mappings with AMS status and sync weights
    from datetime import timezone
    from datetime import datetime as dt

    for ams_unit in ams_status:
        for tray in ams_unit.trays:
            # Find matching mapping
            mapping = next(
                (m for m in mappings if m.ams_id == ams_unit.ams_id and m.tray_id == tray.tray_id),
                None,
            )

            if mapping:
                # Update mapping with AMS status
                mapping.last_reported_type = tray.tray_type
                mapping.last_reported_color = tray.tray_color
                mapping.last_reported_remain = tray.remain
                mapping.last_reported_temp_min = tray.nozzle_temp_min
                mapping.last_reported_temp_max = tray.nozzle_temp_max
                mapping.rfid_tag_uid = tray.tag_uid
                mapping.has_filament = tray.remain is not None and tray.remain > 0
                mapping.is_bambu_filament = tray.tag_uid is not None
                mapping.last_status_at = dt.now(timezone.utc)

                # Sync weight to mapped spool
                if mapping.spool and tray.remain is not None:
                    new_weight = (tray.remain / 100) * float(mapping.spool.initial_weight)
                    mapping.spool.current_weight = new_weight
                    mapping.last_synced_at = dt.now(timezone.utc)

    await db.commit()

    # Return updated list
    return await list_ams_slots(printer_id, user, tenant, db)
