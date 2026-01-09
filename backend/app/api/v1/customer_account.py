"""Customer account API endpoints.

Handles customer profile, addresses, and order history.
All endpoints require customer authentication.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.customer_dependencies import CurrentCustomer
from app.database import get_db
from app.models.customer import Customer, CustomerAddress
from app.models.order import Order
from app.models.return_request import ReturnItem, ReturnRequest, ReturnStatus
from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressListResponse,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerOrderListResponse,
    CustomerOrderResponse,
    CustomerResponse,
    CustomerUpdate,
    CustomerWithAddresses,
)

router = APIRouter()


# ============================================
# Profile Endpoints
# ============================================


@router.get("/profile", response_model=CustomerWithAddresses)
async def get_profile(
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Get current customer profile with addresses."""
    # Reload with addresses
    result = await db.execute(
        select(Customer).where(Customer.id == customer.id).options(selectinload(Customer.addresses))
    )
    customer = result.scalar_one()

    return CustomerWithAddresses.model_validate(customer)


@router.put("/profile", response_model=CustomerResponse)
async def update_profile(
    data: CustomerUpdate,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Update customer profile."""
    if data.full_name is not None:
        customer.full_name = data.full_name
    if data.phone is not None:
        customer.phone = data.phone
    if data.marketing_consent is not None:
        customer.marketing_consent = data.marketing_consent
        if data.marketing_consent and not customer.marketing_consent_at:
            customer.marketing_consent_at = datetime.now(timezone.utc)

    customer.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)


# ============================================
# Address Endpoints
# ============================================


@router.get("/addresses", response_model=CustomerAddressListResponse)
async def list_addresses(
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """List all customer addresses."""
    result = await db.execute(
        select(CustomerAddress)
        .where(CustomerAddress.customer_id == customer.id)
        .order_by(desc(CustomerAddress.is_default), CustomerAddress.label)
    )
    addresses = result.scalars().all()

    return CustomerAddressListResponse(
        items=[CustomerAddressResponse.model_validate(addr) for addr in addresses],
        total=len(addresses),
    )


@router.post("/addresses", response_model=CustomerAddressResponse, status_code=201)
async def create_address(
    data: CustomerAddressCreate,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Create a new address."""
    # If this is marked as default, unset other defaults
    if data.is_default:
        await db.execute(select(CustomerAddress).where(CustomerAddress.customer_id == customer.id))
        existing = await db.execute(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer.id,
                CustomerAddress.is_default.is_(True),
            )
        )
        for addr in existing.scalars().all():
            addr.is_default = False

    address = CustomerAddress(
        customer_id=customer.id,
        tenant_id=customer.tenant_id,
        label=data.label,
        is_default=data.is_default,
        recipient_name=data.recipient_name,
        phone=data.phone,
        line1=data.line1,
        line2=data.line2,
        city=data.city,
        county=data.county,
        postcode=data.postcode,
        country=data.country,
    )

    db.add(address)
    await db.commit()
    await db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


@router.get("/addresses/{address_id}", response_model=CustomerAddressResponse)
async def get_address(
    address_id: UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific address."""
    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    return CustomerAddressResponse.model_validate(address)


@router.put("/addresses/{address_id}", response_model=CustomerAddressResponse)
async def update_address(
    address_id: UUID,
    data: CustomerAddressUpdate,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Update an address."""
    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # If setting as default, unset other defaults
    if data.is_default is True and not address.is_default:
        existing = await db.execute(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer.id,
                CustomerAddress.is_default.is_(True),
                CustomerAddress.id != address_id,
            )
        )
        for addr in existing.scalars().all():
            addr.is_default = False

    # Update fields
    if data.label is not None:
        address.label = data.label
    if data.is_default is not None:
        address.is_default = data.is_default
    if data.recipient_name is not None:
        address.recipient_name = data.recipient_name
    if data.phone is not None:
        address.phone = data.phone
    if data.line1 is not None:
        address.line1 = data.line1
    if data.line2 is not None:
        address.line2 = data.line2
    if data.city is not None:
        address.city = data.city
    if data.county is not None:
        address.county = data.county
    if data.postcode is not None:
        address.postcode = data.postcode
    if data.country is not None:
        address.country = data.country

    address.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


@router.delete("/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id: UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Delete an address."""
    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    await db.delete(address)
    await db.commit()


@router.post("/addresses/{address_id}/set-default", response_model=CustomerAddressResponse)
async def set_default_address(
    address_id: UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Set an address as the default."""
    result = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # Unset other defaults
    existing = await db.execute(
        select(CustomerAddress).where(
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.is_default.is_(True),
            CustomerAddress.id != address_id,
        )
    )
    for addr in existing.scalars().all():
        addr.is_default = False

    # Set this as default
    address.is_default = True
    await db.commit()
    await db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


# ============================================
# Order History Endpoints
# ============================================


@router.get("/orders", response_model=CustomerOrderListResponse)
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    customer: CurrentCustomer = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List customer's order history.

    Returns orders placed by this customer, ordered by most recent first.
    """
    # Base query - find orders by customer email for now
    # TODO: Add customer_id FK to orders after migration
    query = (
        select(Order)
        .where(
            Order.tenant_id == customer.tenant_id,
            func.lower(Order.customer_email) == customer.email.lower(),
        )
        .options(selectinload(Order.items))
        .order_by(desc(Order.created_at))
    )

    # Get total count
    count_query = select(func.count(Order.id)).where(
        Order.tenant_id == customer.tenant_id,
        func.lower(Order.customer_email) == customer.email.lower(),
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get orders with pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    return CustomerOrderListResponse(
        items=[CustomerOrderResponse.model_validate(order) for order in orders],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/orders/{order_id}", response_model=CustomerOrderResponse)
async def get_order(
    order_id: UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order."""
    result = await db.execute(
        select(Order)
        .where(
            Order.id == order_id,
            Order.tenant_id == customer.tenant_id,
            func.lower(Order.customer_email) == customer.email.lower(),
        )
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return CustomerOrderResponse.model_validate(order)


# ============================================
# Return Request Endpoints
# ============================================


from app.schemas.return_request import (
    CustomerReturnListResponse,
    CustomerReturnResponse,
    ReturnItemResponse,
    ReturnRequestCreate,
)


def _build_customer_return_response(return_request: ReturnRequest) -> CustomerReturnResponse:
    """Build customer return response."""
    return CustomerReturnResponse(
        id=return_request.id,
        rma_number=return_request.rma_number,
        status=return_request.status,
        reason=return_request.reason,
        reason_details=return_request.reason_details,
        requested_action=return_request.requested_action,
        created_at=return_request.created_at,
        approved_at=return_request.approved_at,
        received_at=return_request.received_at,
        completed_at=return_request.completed_at,
        refund_amount=return_request.refund_amount,
        return_tracking_number=return_request.return_tracking_number,
        return_label_url=return_request.return_label_url,
        items=[
            ReturnItemResponse(
                id=item.id,
                order_item_id=item.order_item_id,
                quantity=item.quantity,
                reason=item.reason,
                condition_notes=item.condition_notes,
                is_restockable=item.is_restockable,
                product_name=item.order_item.product_name if item.order_item else None,
                product_sku=item.order_item.product_sku if item.order_item else None,
                unit_price=item.order_item.unit_price if item.order_item else None,
            )
            for item in return_request.items
        ],
        order_number=return_request.order.order_number if return_request.order else None,
    )


@router.get("/returns", response_model=CustomerReturnListResponse)
async def list_returns(
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """List all return requests for the customer."""
    result = await db.execute(
        select(ReturnRequest)
        .where(
            ReturnRequest.tenant_id == customer.tenant_id,
            func.lower(ReturnRequest.customer_email) == customer.email.lower(),
        )
        .options(
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.order),
        )
        .order_by(desc(ReturnRequest.created_at))
    )
    return_requests = result.scalars().all()

    return CustomerReturnListResponse(
        items=[_build_customer_return_response(rr) for rr in return_requests],
        total=len(return_requests),
    )


@router.get("/returns/{return_id}", response_model=CustomerReturnResponse)
async def get_return(
    return_id: UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific return request."""
    result = await db.execute(
        select(ReturnRequest)
        .where(
            ReturnRequest.id == return_id,
            ReturnRequest.tenant_id == customer.tenant_id,
            func.lower(ReturnRequest.customer_email) == customer.email.lower(),
        )
        .options(
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.order),
        )
    )
    return_request = result.scalar_one_or_none()

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    return _build_customer_return_response(return_request)


@router.post("/orders/{order_id}/return", response_model=CustomerReturnResponse, status_code=201)
async def create_return_request(
    order_id: UUID,
    data: ReturnRequestCreate,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a return request for an order.

    Customer must own the order to create a return.
    """
    # Find the order
    order_result = await db.execute(
        select(Order)
        .where(
            Order.id == order_id,
            Order.tenant_id == customer.tenant_id,
            func.lower(Order.customer_email) == customer.email.lower(),
        )
        .options(selectinload(Order.items))
    )
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if order is returnable (shipped or delivered)
    if order.status not in ["shipped", "delivered"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be shipped or delivered to request a return",
        )

    # Check for existing open return request
    existing_return = await db.execute(
        select(ReturnRequest).where(
            ReturnRequest.order_id == order_id,
            ReturnRequest.status.in_(
                [
                    ReturnStatus.REQUESTED,
                    ReturnStatus.APPROVED,
                    ReturnStatus.RECEIVED,
                ]
            ),
        )
    )
    if existing_return.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An open return request already exists for this order",
        )

    # Validate return items
    order_item_ids = {item.id for item in order.items}
    for return_item in data.items:
        if return_item.order_item_id not in order_item_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order item {return_item.order_item_id} not found in this order",
            )

        # Check quantity
        order_item = next(i for i in order.items if i.id == return_item.order_item_id)
        if return_item.quantity > order_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Return quantity exceeds ordered quantity for {order_item.product_name}",
            )

    # Generate RMA number
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    rma_count_result = await db.execute(
        select(func.count(ReturnRequest.id)).where(ReturnRequest.rma_number.like(f"RMA-{today}-%"))
    )
    rma_seq = (rma_count_result.scalar() or 0) + 1
    rma_number = f"RMA-{today}-{rma_seq:03d}"

    # Create return request
    return_request = ReturnRequest(
        tenant_id=customer.tenant_id,
        rma_number=rma_number,
        order_id=order_id,
        customer_id=customer.id,
        customer_email=customer.email,
        customer_name=customer.full_name,
        status=ReturnStatus.REQUESTED,
        reason=data.reason,
        reason_details=data.reason_details,
        requested_action=data.requested_action,
    )
    db.add(return_request)
    await db.flush()  # Get the ID

    # Create return items
    for item_data in data.items:
        return_item = ReturnItem(
            return_request_id=return_request.id,
            order_item_id=item_data.order_item_id,
            quantity=item_data.quantity,
            reason=item_data.reason,
        )
        db.add(return_item)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(ReturnRequest)
        .where(ReturnRequest.id == return_request.id)
        .options(
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.order),
        )
    )
    return_request = result.scalar_one()

    # TODO: Send return request confirmation email

    return _build_customer_return_response(return_request)


@router.post("/returns/{return_id}/cancel", response_model=CustomerReturnResponse)
async def cancel_return_request(
    return_id: UUID,
    customer: CurrentCustomer,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a return request (only if still in requested status)."""
    result = await db.execute(
        select(ReturnRequest)
        .where(
            ReturnRequest.id == return_id,
            ReturnRequest.tenant_id == customer.tenant_id,
            func.lower(ReturnRequest.customer_email) == customer.email.lower(),
        )
        .options(
            selectinload(ReturnRequest.items).selectinload(ReturnItem.order_item),
            selectinload(ReturnRequest.order),
        )
    )
    return_request = result.scalar_one_or_none()

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status != ReturnStatus.REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel return requests in 'requested' status",
        )

    return_request.status = ReturnStatus.CANCELLED
    return_request.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(return_request)

    return _build_customer_return_response(return_request)
