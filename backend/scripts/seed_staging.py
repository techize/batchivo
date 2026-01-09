#!/usr/bin/env python3
"""Comprehensive seed script for staging environment.

Creates test data for the mystmereforge tenant including:
- Tenant and sales channel
- Categories
- Test products (dragons)
- Test customers
- Sample orders
- Discount codes

Designed to be idempotent - safe to run multiple times.

Run with: DATABASE_URL=<staging_db_url> poetry run python scripts/seed_staging.py
Or via kubectl exec into the backend pod in nozzly-staging namespace.
"""

import asyncio
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select, text

from app.database import async_session_maker
from app.models.tenant import Tenant
from app.models.sales_channel import SalesChannel
from app.models.category import Category
from app.models.product import Product
from app.models.product_pricing import ProductPricing
from app.models.customer import Customer, CustomerAddress
from app.models.order import Order, OrderItem, OrderStatus
from app.models.discount import DiscountCode, DiscountType


# Shop categories for Mystmereforge
SHOP_CATEGORIES = [
    {
        "name": "Dragons",
        "slug": "dragons",
        "description": "Articulated dragons - each one unique and named with their own personality and backstory",
        "display_order": 1,
    },
    {
        "name": "Dinosaurs",
        "slug": "dinosaurs",
        "description": "Articulated dinosaurs and prehistoric creatures",
        "display_order": 2,
    },
    {
        "name": "Wildlife",
        "slug": "wildlife",
        "description": "British wildlife scenes and dioramas",
        "display_order": 3,
    },
    {
        "name": "Toys & Trinkets",
        "slug": "toys",
        "description": "Fun fidget toys and desk companions",
        "display_order": 4,
    },
]

# Test products (dragons with backstories)
TEST_PRODUCTS = [
    {
        "sku": "DRAGON-STAGING-001",
        "name": "Ember the Fire Drake",
        "description": "A majestic fire drake with crimson scales",
        "shop_description": "<p>Meet <strong>Ember</strong>, a spirited fire drake who was hatched in the volcanic forges of Mount Cinder.</p><p>With scales that shimmer like molten lava and eyes that glow with ancient wisdom, Ember brings warmth wherever they go.</p>",
        "feature_title": "Ember",
        "backstory": "Born during the Great Eruption, Ember learned to harness the power of flames not for destruction, but for creation. Now a master smith, Ember forges magical artifacts for worthy adventurers.",
        "is_dragon": True,
        "is_featured": True,
        "shop_visible": True,
        "units_in_stock": 3,
        "price": Decimal("35.00"),
    },
    {
        "sku": "DRAGON-STAGING-002",
        "name": "Frost the Ice Wyrm",
        "description": "An elegant ice wyrm with crystalline scales",
        "shop_description": "<p><strong>Frost</strong> glides through the frozen peaks of the Northern Reaches, their crystalline scales catching the aurora's light.</p>",
        "feature_title": "Frost",
        "backstory": "Guardian of the Frozen Library, Frost protects ancient knowledge preserved in ice. Those who prove worthy may receive a whispered secret from ages past.",
        "is_dragon": True,
        "is_featured": True,
        "shop_visible": True,
        "units_in_stock": 2,
        "price": Decimal("38.00"),
    },
    {
        "sku": "DRAGON-STAGING-003",
        "name": "Shadow the Night Serpent",
        "description": "A mysterious night serpent with dark iridescent scales",
        "shop_description": "<p><strong>Shadow</strong> emerges only when the moon is new, their dark scales shimmering with hidden stars.</p>",
        "feature_title": "Shadow",
        "backstory": "Once a dragon of light, Shadow chose darkness to protect their realm from a greater threat. Their sacrifice is remembered in the constellations.",
        "is_dragon": True,
        "is_featured": False,
        "shop_visible": True,
        "units_in_stock": 5,
        "price": Decimal("32.00"),
    },
    {
        "sku": "TOY-STAGING-001",
        "name": "Fidget Gecko",
        "description": "Articulated gecko fidget toy",
        "shop_description": "<p>A fun, fully articulated gecko that's perfect for fidgeting at your desk.</p>",
        "feature_title": None,
        "backstory": None,
        "is_dragon": False,
        "is_featured": False,
        "shop_visible": True,
        "units_in_stock": 10,
        "price": Decimal("12.00"),
    },
]

# Test customers
TEST_CUSTOMERS = [
    {
        "email": "test.customer@staging.mystmereforge.co.uk",
        "full_name": "Test Customer",
        "phone": "07700 900001",
        "password": "staging123",
        "address": {
            "label": "Home",
            "recipient_name": "Test Customer",
            "line1": "123 Test Street",
            "city": "Testington",
            "county": "Norfolk",
            "postcode": "NR1 1AA",
            "country": "United Kingdom",
            "is_default": True,
        },
    },
    {
        "email": "jane.smith@staging.mystmereforge.co.uk",
        "full_name": "Jane Smith",
        "phone": "07700 900002",
        "password": "staging123",
        "address": {
            "label": "Work",
            "recipient_name": "Jane Smith",
            "line1": "456 Business Park",
            "line2": "Unit 7",
            "city": "Norwich",
            "county": "Norfolk",
            "postcode": "NR2 2BB",
            "country": "United Kingdom",
            "is_default": True,
        },
    },
]

# Discount codes
TEST_DISCOUNTS = [
    {
        "code": "STAGING10",
        "name": "Staging 10% Off",
        "description": "Test discount code for staging - 10% off",
        "discount_type": DiscountType.PERCENTAGE.value,
        "amount": Decimal("10.00"),
        "min_order_amount": Decimal("20.00"),
        "max_uses": None,  # Unlimited
    },
    {
        "code": "TESTFIVER",
        "name": "Test £5 Off",
        "description": "Test discount code for staging - £5 off",
        "discount_type": DiscountType.FIXED_AMOUNT.value,
        "amount": Decimal("5.00"),
        "min_order_amount": Decimal("25.00"),
        "max_uses": 100,
    },
    {
        "code": "FREESHIP",
        "name": "Free Shipping Test",
        "description": "Test code for free shipping testing",
        "discount_type": DiscountType.FIXED_AMOUNT.value,
        "amount": Decimal("3.95"),  # Standard shipping cost
        "min_order_amount": Decimal("30.00"),
        "max_uses": 50,
    },
]


def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


async def seed_tenant_and_channel(session) -> tuple:
    """Create or get mystmereforge tenant and sales channel."""
    # Check for existing tenant
    result = await session.execute(select(Tenant).where(Tenant.slug == "mystmereforge"))
    tenant = result.scalar_one_or_none()

    if not tenant:
        print("Creating Mystmereforge tenant...")
        tenant = Tenant(
            id=uuid4(),
            name="Mystmere Forge",
            slug="mystmereforge",
            description="Handcrafted 3D printed dragons, toys, and collectables",
            is_active=True,
        )
        session.add(tenant)
        await session.flush()
        print(f"  Created tenant: {tenant.id}")
    else:
        print(f"  Tenant exists: {tenant.id}")

    # Check for existing sales channel
    result = await session.execute(
        select(SalesChannel).where(
            SalesChannel.tenant_id == tenant.id,
            SalesChannel.name == "Mystmereforge Shop",
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        print("Creating Mystmereforge Shop sales channel...")
        channel = SalesChannel(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Mystmereforge Shop",
            platform_type="online_shop",
            fee_percentage=Decimal("2.9"),
            fee_fixed=Decimal("0.30"),
            monthly_cost=Decimal("0"),
            is_active=True,
        )
        session.add(channel)
        await session.flush()
        print(f"  Created sales channel: {channel.id}")
    else:
        print(f"  Sales channel exists: {channel.id}")

    return tenant, channel


async def seed_categories(session, tenant_id) -> dict:
    """Create shop categories and return slug->category mapping."""
    print("\nSeeding categories...")
    categories = {}

    for cat_data in SHOP_CATEGORIES:
        result = await session.execute(
            select(Category).where(
                Category.tenant_id == tenant_id,
                Category.slug == cat_data["slug"],
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            category = Category(
                id=uuid4(),
                tenant_id=tenant_id,
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                display_order=cat_data["display_order"],
                is_active=True,
            )
            session.add(category)
            await session.flush()
            categories[cat_data["slug"]] = category
            print(f"  Created: {cat_data['name']}")
        else:
            categories[cat_data["slug"]] = existing
            print(f"  Exists: {cat_data['name']}")

    return categories


async def seed_products(session, tenant_id, channel_id, categories) -> list:
    """Create test products with pricing."""
    print("\nSeeding test products...")
    products = []
    dragons_category = categories.get("dragons")
    toys_category = categories.get("toys")

    for prod_data in TEST_PRODUCTS:
        result = await session.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.sku == prod_data["sku"],
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            product = Product(
                id=uuid4(),
                tenant_id=tenant_id,
                sku=prod_data["sku"],
                name=prod_data["name"],
                description=prod_data["description"],
                shop_description=prod_data["shop_description"],
                feature_title=prod_data["feature_title"],
                backstory=prod_data["backstory"],
                is_dragon=prod_data["is_dragon"],
                is_featured=prod_data["is_featured"],
                shop_visible=prod_data["shop_visible"],
                units_in_stock=prod_data["units_in_stock"],
                is_active=True,
            )
            session.add(product)
            await session.flush()

            # Add to appropriate category via association table
            category_to_add = None
            if prod_data["is_dragon"] and dragons_category:
                category_to_add = dragons_category
            elif not prod_data["is_dragon"] and toys_category:
                category_to_add = toys_category

            if category_to_add:
                # Insert directly into association table to avoid lazy loading
                await session.execute(
                    text(
                        "INSERT INTO product_categories (product_id, category_id, tenant_id) VALUES (:product_id, :category_id, :tenant_id)"
                    ),
                    {
                        "product_id": str(product.id),
                        "category_id": str(category_to_add.id),
                        "tenant_id": str(tenant_id),
                    },
                )

            # Create pricing for the shop channel
            pricing = ProductPricing(
                id=uuid4(),
                product_id=product.id,
                sales_channel_id=channel_id,
                list_price=float(prod_data["price"]),
                is_active=True,
            )
            session.add(pricing)

            products.append(product)
            print(f"  Created: {prod_data['name']} @ £{prod_data['price']}")
        else:
            products.append(existing)
            print(f"  Exists: {prod_data['name']}")

    return products


async def seed_customers(session, tenant_id) -> list:
    """Create test customer accounts."""
    print("\nSeeding test customers...")
    customers = []

    for cust_data in TEST_CUSTOMERS:
        result = await session.execute(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.email == cust_data["email"],
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            customer = Customer(
                id=uuid4(),
                tenant_id=tenant_id,
                email=cust_data["email"],
                hashed_password=hash_password(cust_data["password"]),
                full_name=cust_data["full_name"],
                phone=cust_data["phone"],
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
                is_active=True,
            )
            session.add(customer)
            await session.flush()

            # Add address
            addr_data = cust_data["address"]
            address = CustomerAddress(
                id=uuid4(),
                customer_id=customer.id,
                tenant_id=tenant_id,
                label=addr_data["label"],
                recipient_name=addr_data["recipient_name"],
                line1=addr_data["line1"],
                line2=addr_data.get("line2"),
                city=addr_data["city"],
                county=addr_data.get("county"),
                postcode=addr_data["postcode"],
                country=addr_data["country"],
                is_default=addr_data["is_default"],
            )
            session.add(address)

            customers.append(customer)
            print(f"  Created: {cust_data['email']} (password: {cust_data['password']})")
        else:
            customers.append(existing)
            print(f"  Exists: {cust_data['email']}")

    return customers


async def seed_orders(session, tenant_id, channel_id, products, customers) -> list:
    """Create sample orders for testing."""
    print("\nSeeding sample orders...")
    orders = []

    if not products or not customers:
        print("  Skipping - no products or customers")
        return orders

    # Sample order data
    sample_orders = [
        {
            "customer_idx": 0,
            "product_idx": 0,
            "quantity": 1,
            "status": OrderStatus.DELIVERED,
            "days_ago": 7,
        },
        {
            "customer_idx": 1,
            "product_idx": 1,
            "quantity": 1,
            "status": OrderStatus.SHIPPED,
            "days_ago": 2,
        },
        {
            "customer_idx": 0,
            "product_idx": 2,
            "quantity": 2,
            "status": OrderStatus.PROCESSING,
            "days_ago": 1,
        },
        {
            "customer_idx": 1,
            "product_idx": 3,
            "quantity": 3,
            "status": OrderStatus.PENDING,
            "days_ago": 0,
        },
    ]

    for i, order_data in enumerate(sample_orders):
        if order_data["product_idx"] >= len(products):
            continue
        if order_data["customer_idx"] >= len(customers):
            continue

        product = products[order_data["product_idx"]]
        customer = customers[order_data["customer_idx"]]
        order_number = f"MF-STAGING-{i+1:03d}"

        # Check if order exists
        result = await session.execute(select(Order).where(Order.order_number == order_number))
        existing = result.scalar_one_or_none()

        if not existing:
            # Get product price
            result = await session.execute(
                select(ProductPricing).where(
                    ProductPricing.product_id == product.id,
                    ProductPricing.sales_channel_id == channel_id,
                )
            )
            pricing = result.scalar_one_or_none()
            unit_price = Decimal(str(pricing.list_price)) if pricing else Decimal("25.00")

            quantity = order_data["quantity"]
            subtotal = unit_price * quantity
            shipping = Decimal("3.95")
            total = subtotal + shipping

            order_date = datetime.now(timezone.utc) - timedelta(days=order_data["days_ago"])

            order = Order(
                id=uuid4(),
                tenant_id=tenant_id,
                order_number=order_number,
                sales_channel_id=channel_id,
                customer_id=customer.id,
                status=order_data["status"],
                customer_email=customer.email,
                customer_name=customer.full_name,
                customer_phone=customer.phone,
                shipping_address_line1="123 Test Street",
                shipping_city="Norwich",
                shipping_county="Norfolk",
                shipping_postcode="NR1 1AA",
                shipping_country="United Kingdom",
                shipping_method="Royal Mail 2nd Class",
                shipping_cost=shipping,
                subtotal=subtotal,
                total=total,
                currency="GBP",
                payment_provider="square",
                payment_id=f"staging_payment_{uuid4().hex[:8]}",
                payment_status="completed",
                confirmation_email_sent=True,
                confirmation_email_sent_at=order_date,
                created_at=order_date,
            )

            if order_data["status"] in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
                order.shipped_at = order_date + timedelta(days=1)
                order.tracking_number = f"STAGING{i+1:06d}GB"
                order.shipped_email_sent = True

            if order_data["status"] == OrderStatus.DELIVERED:
                order.delivered_at = order_date + timedelta(days=3)
                order.delivered_email_sent = True

            session.add(order)
            await session.flush()

            # Add order item
            order_item = OrderItem(
                id=uuid4(),
                tenant_id=tenant_id,
                order_id=order.id,
                product_id=product.id,
                product_sku=product.sku,
                product_name=product.name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=subtotal,
            )
            session.add(order_item)

            orders.append(order)
            print(f"  Created: {order_number} ({order_data['status']}) - {product.name}")
        else:
            orders.append(existing)
            print(f"  Exists: {order_number}")

    return orders


async def seed_discounts(session, tenant_id) -> list:
    """Create test discount codes."""
    print("\nSeeding discount codes...")
    discounts = []
    now = datetime.now(timezone.utc)

    for disc_data in TEST_DISCOUNTS:
        result = await session.execute(
            select(DiscountCode).where(
                DiscountCode.tenant_id == tenant_id,
                DiscountCode.code == disc_data["code"],
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            discount = DiscountCode(
                id=uuid4(),
                tenant_id=tenant_id,
                code=disc_data["code"],
                name=disc_data["name"],
                description=disc_data["description"],
                discount_type=disc_data["discount_type"],
                amount=disc_data["amount"],
                min_order_amount=disc_data["min_order_amount"],
                max_uses=disc_data["max_uses"],
                valid_from=now,
                valid_to=now + timedelta(days=365),  # Valid for 1 year
                is_active=True,
            )
            session.add(discount)
            discounts.append(discount)
            print(f"  Created: {disc_data['code']} ({disc_data['name']})")
        else:
            discounts.append(existing)
            print(f"  Exists: {disc_data['code']}")

    return discounts


async def seed_staging():
    """Main seed function - creates all test data."""
    print("=" * 60)
    print("STAGING SEED SCRIPT")
    print("=" * 60)

    async with async_session_maker() as session:
        try:
            # 1. Create tenant and sales channel
            tenant, channel = await seed_tenant_and_channel(session)

            # 2. Create categories
            categories = await seed_categories(session, tenant.id)

            # 3. Create test products
            products = await seed_products(session, tenant.id, channel.id, categories)

            # 4. Create test customers
            customers = await seed_customers(session, tenant.id)

            # 5. Create sample orders
            orders = await seed_orders(session, tenant.id, channel.id, products, customers)

            # 6. Create discount codes
            discounts = await seed_discounts(session, tenant.id)

            # Commit all changes
            await session.commit()

            print("\n" + "=" * 60)
            print("SEED COMPLETE")
            print("=" * 60)
            print(f"\nTenant ID: {tenant.id}")
            print(f"Sales Channel ID: {channel.id}")
            print("\nCreated/Verified:")
            print(f"  - {len(categories)} categories")
            print(f"  - {len(products)} products")
            print(f"  - {len(customers)} customers")
            print(f"  - {len(orders)} orders")
            print(f"  - {len(discounts)} discount codes")
            print("\nTest credentials:")
            for cust in TEST_CUSTOMERS:
                print(f"  - {cust['email']} / {cust['password']}")
            print("\nDiscount codes:")
            for disc in TEST_DISCOUNTS:
                print(f"  - {disc['code']}: {disc['name']}")

            return tenant.id, channel.id

        except Exception as e:
            await session.rollback()
            print(f"\nERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_staging())
