"""Pytest configuration and fixtures for tests."""

import os
from typing import AsyncGenerator
from uuid import uuid4

# SECURITY: Set test SECRET_KEY before any app imports trigger Settings loading
# This is a cryptographically secure test key (not used in production)
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-for-pytest-only-do-not-use-in-production-minimum-32-chars",
)

import boto3
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from decimal import Decimal

from app.database import Base, get_db
from app.main import app
from app.models.customer import Customer
from app.models.material import MaterialType
from app.models.product import Product
from app.models.spool import Spool
from app.models.tenant import Tenant
from app.models.user import User


# Configure anyio to only use asyncio backend (not trio)
@pytest.fixture
def anyio_backend():
    """Tell anyio pytest plugin to only use asyncio, not trio."""
    return "asyncio"


# Test database URL - use DATABASE_URL from env (CI uses PostgreSQL),
# fallback to SQLite for local testing (but SQLite doesn't support JSONB)
_BASE_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# For pytest-xdist parallel execution, each worker needs its own database
# Worker IDs are like "gw0", "gw1", etc. or "master" for single-process
_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "")

if _WORKER_ID and not _BASE_DATABASE_URL.startswith("sqlite"):
    # Append worker ID to database name for isolation
    # Works with any database name (test_batchivo, test_unit, test_int, test_api, etc.)
    # e.g., postgresql://user:pass@host/test_unit -> postgresql://user:pass@host/test_unit_gw0
    import re

    TEST_DATABASE_URL = re.sub(r"/([^/]+)$", rf"/\1_{_WORKER_ID}", _BASE_DATABASE_URL)
else:
    TEST_DATABASE_URL = _BASE_DATABASE_URL

# Determine if we're using SQLite (for connect_args)
_IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")


async def _drop_all_tables(conn, is_sqlite: bool):
    """Drop all tables, handling PostgreSQL circular FKs with CASCADE."""
    if is_sqlite:
        await conn.run_sync(Base.metadata.drop_all)
    else:
        from sqlalchemy import text

        # Get all table names and drop them with CASCADE to handle circular FKs
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = result.fetchall()
        if tables:
            table_names = ", ".join(f'"{t[0]}"' for t in tables)
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_names} CASCADE"))


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine (function-scoped for test isolation)."""
    # SQLite needs check_same_thread=False, PostgreSQL doesn't use connect_args
    connect_args = {"check_same_thread": False} if _IS_SQLITE else {}
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args=connect_args,
    )

    # Drop any existing tables first (important for PostgreSQL persistence)
    async with engine.begin() as conn:
        await _drop_all_tables(conn, _IS_SQLITE)
        await conn.run_sync(Base.metadata.create_all)

        # Create PostgreSQL full-text search trigger (not created by create_all)
        if not _IS_SQLITE:
            await conn.execute(
                text("""
                CREATE OR REPLACE FUNCTION products_search_trigger() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector :=
                        setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(NEW.sku, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
                        setweight(to_tsvector('english', COALESCE(NEW.shop_description, '')), 'C');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;
            """)
            )
            await conn.execute(
                text("""
                DROP TRIGGER IF EXISTS products_search_update ON products;
            """)
            )
            await conn.execute(
                text("""
                CREATE TRIGGER products_search_update
                    BEFORE INSERT OR UPDATE ON products
                    FOR EACH ROW
                    EXECUTE FUNCTION products_search_trigger();
            """)
            )

    yield engine

    # Cleanup after test
    async with engine.begin() as conn:
        await _drop_all_tables(conn, _IS_SQLITE)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def seed_material_types(db_session: AsyncSession):
    """Seed the database with standard material types."""
    material_types = [
        {
            "code": "PLA",
            "name": "PLA (Polylactic Acid)",
            "description": "Standard 3D printing filament",
        },
        {
            "code": "PETG",
            "name": "PETG (Polyethylene Terephthalate Glycol)",
            "description": "Strong, durable filament",
        },
        {
            "code": "ABS",
            "name": "ABS (Acrylonitrile Butadiene Styrene)",
            "description": "Engineering-grade filament",
        },
        {
            "code": "TPU",
            "name": "TPU (Thermoplastic Polyurethane)",
            "description": "Flexible filament",
        },
        {
            "code": "ASA",
            "name": "ASA (Acrylonitrile Styrene Acrylate)",
            "description": "UV-resistant filament",
        },
        {
            "code": "Nylon",
            "name": "Nylon (Polyamide)",
            "description": "Strong, flexible engineering filament",
        },
        {
            "code": "PC",
            "name": "Polycarbonate",
            "description": "High-strength engineering filament",
        },
        {
            "code": "PLA+",
            "name": "PLA+ (Enhanced PLA)",
            "description": "Improved PLA with better strength",
        },
    ]

    for mat_data in material_types:
        material = MaterialType(
            id=uuid4(),
            code=mat_data["code"],
            name=mat_data["name"],
            description=mat_data["description"],
            is_active=True,
        )
        db_session.add(material)

    await db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession, seed_material_types, test_user: User, test_tenant: Tenant
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with database session and auth overrides."""
    from app.auth.dependencies import get_current_user, get_current_tenant

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    async def override_get_current_tenant():
        return test_tenant

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    # Disable rate limiting for tests
    app.state.limiter.enabled = False

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Re-enable rate limiting after test
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


# Alias for clearer test naming
async_client = client
db = db_session  # Alias for consistency with tests


@pytest_asyncio.fixture(scope="function")
async def unauthenticated_client(
    db_session: AsyncSession, seed_material_types
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client WITHOUT authentication overrides for testing auth."""
    from app.database import get_db

    async def override_get_db():
        yield db_session

    # Only override the database, not auth
    app.dependency_overrides[get_db] = override_get_db

    # Disable rate limiting for tests
    app.state.limiter.enabled = False

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Re-enable rate limiting after test
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant with unique slug (avoids PostgreSQL duplicate key issues)."""
    # Use UUID suffix to ensure uniqueness across parallel tests
    unique_id = str(uuid4())[:8]
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-tenant-{unique_id}",
        settings={
            "default_labor_rate": 20.0,
            "currency": "USD",
        },
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user with proper password hashing."""
    from app.auth.password import get_password_hash
    from app.models.user import UserTenant, UserRole

    # Use unique email per test to avoid PostgreSQL duplicate key issues
    unique_id = str(uuid4())[:8]
    user = User(
        id=uuid4(),
        email=f"test-{unique_id}@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()  # Flush to get user.id

    # Create user-tenant relationship
    user_tenant = UserTenant(
        user_id=user.id,
        tenant_id=test_tenant.id,
        role=UserRole.ADMIN,
    )
    db_session.add(user_tenant)

    await db_session.commit()

    # Refresh user with relationships loaded for proper testing
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.user_tenants))
    )
    user = result.scalar_one()
    return user


@pytest.fixture
def auth_headers(test_user: User, test_tenant: Tenant) -> dict:
    """Create auth headers for test requests (mock JWT)."""
    # In production, this would be a real JWT token
    # For tests, we'll mock the authentication
    return {
        "Authorization": f"Bearer mock-token-{test_user.id}",
        "X-Tenant-ID": str(test_tenant.id),
    }


@pytest_asyncio.fixture(scope="function")
async def test_material_type(db_session: AsyncSession, seed_material_types) -> MaterialType:
    """Get the PLA material type from seeded data."""
    from sqlalchemy import select

    # Query for the PLA material type that was seeded
    result = await db_session.execute(select(MaterialType).where(MaterialType.code == "PLA"))
    material_type = result.scalar_one()
    return material_type


@pytest_asyncio.fixture(scope="function")
async def test_spool(
    db_session: AsyncSession, test_tenant: Tenant, test_material_type: MaterialType
) -> Spool:
    """Create a test spool."""
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        spool_id="TEST-SPOOL-001",
        brand="Test Brand",
        color="Red",
        initial_weight=1000.0,
        current_weight=800.0,
        purchase_price=Decimal("25.00"),
        is_active=True,
    )
    db_session.add(spool)
    await db_session.commit()
    await db_session.refresh(spool)
    return spool


@pytest_asyncio.fixture(scope="function")
async def test_product(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a test product."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TEST-PROD-001",
        name="Test Product",
        description="Test product for production runs",
        units_in_stock=10,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture(scope="function")
async def test_model(db_session: AsyncSession, test_tenant: Tenant):
    """Create a test 3D model (printable part)."""
    from app.models.model import Model
    from decimal import Decimal

    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TEST-MODEL-001",
        name="Test 3D Model",
        description="Test 3D model for production runs",
        print_time_minutes=60,
        labor_hours=Decimal("0.25"),  # 15 minutes = 0.25 hours
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture(scope="function")
async def test_model_with_prints_per_plate(db_session: AsyncSession, test_tenant: Tenant):
    """Create a test 3D model with prints_per_plate set for multi-plate tests."""
    from app.models.model import Model
    from decimal import Decimal

    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TEST-MODEL-002",
        name="Multi-Plate Test Model",
        description="Test 3D model for multi-plate production runs",
        print_time_minutes=45,
        prints_per_plate=3,
        labor_hours=Decimal("0.25"),
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture(scope="function")
async def test_printer(db_session: AsyncSession, test_tenant: Tenant):
    """Create a test printer."""
    from app.models.printer import Printer
    from decimal import Decimal

    printer = Printer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Bambu A1 Mini",
        manufacturer="Bambu Lab",
        model="A1 Mini",
        bed_size_x_mm=180,
        bed_size_y_mm=180,
        bed_size_z_mm=180,
        nozzle_diameter_mm=Decimal("0.4"),
        default_bed_temp=60,
        default_nozzle_temp=220,
        capabilities={"ams": True, "multi_color": True},
        is_active=True,
    )
    db_session.add(printer)
    await db_session.commit()
    await db_session.refresh(printer)
    return printer


@pytest_asyncio.fixture(scope="function")
async def test_model_printer_config(db_session: AsyncSession, test_model, test_printer):
    """Create a test model printer configuration."""
    from app.models.model_printer_config import ModelPrinterConfig
    from decimal import Decimal

    config = ModelPrinterConfig(
        id=uuid4(),
        model_id=test_model.id,
        printer_id=test_printer.id,
        prints_per_plate=3,
        print_time_minutes=45,
        material_weight_grams=Decimal("30.0"),
        bed_temperature=60,
        nozzle_temperature=220,
        layer_height=Decimal("0.20"),
        infill_percentage=15,
        supports=False,
        brim=True,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture(scope="function")
async def test_product_with_image(
    db_session: AsyncSession, test_tenant: Tenant, test_product: Product, tmp_path
):
    """Create a test product with an image for image API tests."""
    from app.models.product_image import ProductImage
    from PIL import Image as PILImage
    from app.services.image_storage import get_image_storage

    # Get image storage and configure it to use temp path
    storage = get_image_storage()
    storage.base_path = tmp_path
    storage.storage_type = "local"

    # Create product directory
    product_dir = tmp_path / "products" / str(test_product.id)
    product_dir.mkdir(parents=True)

    # Create actual image files (landscape 200x100 for rotation testing)
    image_id = uuid4()
    img = PILImage.new("RGB", (200, 100), color="blue")
    image_path = product_dir / f"{image_id}.jpg"
    img.save(image_path, format="JPEG")

    # Create thumbnail
    thumb = PILImage.new("RGB", (100, 50), color="blue")
    thumb_path = product_dir / f"{image_id}_thumb.jpg"
    thumb.save(thumb_path, format="JPEG")

    # Create database record
    product_image = ProductImage(
        id=image_id,
        tenant_id=test_tenant.id,
        product_id=test_product.id,
        image_url=f"/uploads/products/{test_product.id}/{image_id}.jpg",
        thumbnail_url=f"/uploads/products/{test_product.id}/{image_id}_thumb.jpg",
        alt_text="Test product image",
        display_order=0,
        is_primary=True,
        original_filename="test.jpg",
        file_size=len(img.tobytes()),
        content_type="image/jpeg",
    )
    db_session.add(product_image)
    await db_session.commit()
    await db_session.refresh(product_image)

    return test_product, product_image


@pytest_asyncio.fixture(scope="function")
async def test_designer(db_session: AsyncSession, test_tenant: Tenant):
    """Create a test designer."""
    from app.models.designer import Designer

    designer = Designer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Designer",
        slug="test-designer",
        description="A test designer for unit tests",
        is_active=True,
    )
    db_session.add(designer)
    await db_session.commit()
    await db_session.refresh(designer)
    return designer


@pytest_asyncio.fixture(scope="function")
async def test_customer(db_session: AsyncSession, test_tenant: Tenant) -> Customer:
    """Create a test customer account."""
    from app.auth.password import get_password_hash

    # Use unique email per test to avoid PostgreSQL duplicate key issues
    unique_id = str(uuid4())[:8]
    customer = Customer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"customer-{unique_id}@example.com",
        full_name="Test Customer",
        hashed_password=get_password_hash("customerpass123"),
        is_active=True,
        email_verified=True,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture(scope="function")
async def customer_client(
    db_session: AsyncSession, seed_material_types, test_customer: Customer, test_tenant: Tenant
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client authenticated as a customer."""
    from app.auth.customer_dependencies import get_current_customer, get_current_customer_tenant

    async def override_get_db():
        yield db_session

    async def override_get_current_customer():
        return test_customer

    async def override_get_current_customer_tenant():
        return test_tenant

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_customer] = override_get_current_customer
    app.dependency_overrides[get_current_customer_tenant] = override_get_current_customer_tenant

    # Disable rate limiting for tests
    app.state.limiter.enabled = False

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Re-enable rate limiting after test
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


# =============================================================================
# Storage Type Fixtures (for S3/Local switching in CI)
# =============================================================================

# Test S3 bucket name for moto mocking
TEST_S3_BUCKET = "test-batchivo-images"


@pytest.fixture
def test_storage_type():
    """Get storage type from environment for CI matrix testing.

    Set TEST_STORAGE_TYPE=s3 to run tests against mocked S3.
    Default is 'local' for filesystem storage.
    """
    return os.getenv("TEST_STORAGE_TYPE", "local")


@pytest.fixture
def s3_mock():
    """Create a mocked S3 environment using moto.

    Use this fixture when you need S3 mocking in integration tests.
    """
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=TEST_S3_BUCKET)
        yield conn


@pytest.fixture
def image_storage_fixture(test_storage_type, tmp_path, s3_mock):
    """Get configured image storage based on TEST_STORAGE_TYPE environment variable.

    This fixture provides either local or S3 storage depending on the
    TEST_STORAGE_TYPE environment variable, enabling CI matrix testing.
    """
    from app.services.image_storage import get_image_storage

    storage = get_image_storage()

    if test_storage_type == "s3":
        storage.storage_type = "s3"
        storage._bucket = TEST_S3_BUCKET
        storage._s3_client = s3_mock
    else:
        storage.storage_type = "local"
        storage.base_path = tmp_path
        (tmp_path / "products").mkdir(exist_ok=True)

    return storage
