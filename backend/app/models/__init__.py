"""Database models."""

from app.models.base import TimestampMixin, UUIDMixin
from app.models.consumable import ConsumablePurchase, ConsumableType, ConsumableUsage
from app.models.material import MaterialType

# Model (printed items) - renamed from Product
from app.models.model import Model
from app.models.model_file import ModelFile, ModelFileType
from app.models.model_material import ModelMaterial
from app.models.model_component import ModelComponent

# Printers and printer-specific configurations
from app.models.printer import Printer
from app.models.printer_connection import ConnectionType, PrinterConnection
from app.models.ams_slot_mapping import AMSSlotMapping
from app.models.model_printer_config import ModelPrinterConfig

# Print queue
from app.models.print_job import JobPriority, JobStatus, PrintJob

# Product (sellable items composed of models and/or other products)
from app.models.category import Category, product_categories
from app.models.designer import Designer
from app.models.product import Product
from app.models.product_component import ProductComponent
from app.models.product_image import ProductImage
from app.models.product_model import ProductModel
from app.models.product_pricing import ProductPricing

# Sales channels
from app.models.sales_channel import SalesChannel

# External listings (marketplace integrations)
from app.models.external_listing import ExternalListing

# Orders
from app.models.order import Order, OrderItem, OrderStatus

# Discounts
from app.models.discount import DiscountCode, DiscountType, DiscountUsage

# Payment logging
from app.models.payment_log import PaymentLog, PaymentLogOperation, PaymentLogStatus

# Production runs
from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.production_run_plate import ProductionRunPlate

# Inventory
from app.models.spool import Spool
from app.models.inventory_transaction import InventoryTransaction, TransactionType
from app.models.spoolmandb import SpoolmanDBFilament, SpoolmanDBManufacturer

# Content pages
from app.models.page import Page, PageType

# Customer accounts
from app.models.customer import Customer, CustomerAddress

# Reviews
from app.models.review import Review

# Returns (RMA)
from app.models.return_request import (
    ReturnAction,
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnStatus,
)

# Audit logging
from app.models.audit_log import AuditAction, AuditLog

# Webhooks (outbound)
from app.models.webhook import (
    DeliveryStatus,
    WebhookDelivery,
    WebhookEventType,
    WebhookSubscription,
)

# Webhook Events (inbound)
from app.models.webhook_event import (
    WebhookDeadLetter,
    WebhookEvent,
    WebhookEventSource,
    WebhookEventStatus,
)

# Multi-tenancy
from app.models.tenant import Tenant
from app.models.tenant_module import TenantModule
from app.models.user import User, UserRole, UserTenant

# Platform admin
from app.models.platform_admin import PlatformAdminAuditLog, PlatformSetting

__all__ = [
    # Mixins
    "UUIDMixin",
    "TimestampMixin",
    # Models (printed items)
    "Model",
    "ModelFile",
    "ModelFileType",
    "ModelMaterial",
    "ModelComponent",
    # Printers
    "Printer",
    "PrinterConnection",
    "ConnectionType",
    "AMSSlotMapping",
    "ModelPrinterConfig",
    # Print queue
    "PrintJob",
    "JobPriority",
    "JobStatus",
    # Products (sellable items)
    "Category",
    "product_categories",
    "Designer",
    "Product",
    "ProductComponent",
    "ProductImage",
    "ProductModel",
    "ProductPricing",
    # Sales
    "SalesChannel",
    # External listings
    "ExternalListing",
    # Orders
    "Order",
    "OrderItem",
    "OrderStatus",
    # Discounts
    "DiscountCode",
    "DiscountType",
    "DiscountUsage",
    # Payment logging
    "PaymentLog",
    "PaymentLogOperation",
    "PaymentLogStatus",
    # Production
    "ProductionRun",
    "ProductionRunItem",
    "ProductionRunMaterial",
    "ProductionRunPlate",
    # Inventory
    "Spool",
    "InventoryTransaction",
    "TransactionType",
    "MaterialType",
    # Consumables
    "ConsumableType",
    "ConsumablePurchase",
    "ConsumableUsage",
    # SpoolmanDB reference data
    "SpoolmanDBManufacturer",
    "SpoolmanDBFilament",
    # Content pages
    "Page",
    "PageType",
    # Customer accounts
    "Customer",
    "CustomerAddress",
    # Reviews
    "Review",
    # Returns (RMA)
    "ReturnAction",
    "ReturnItem",
    "ReturnReason",
    "ReturnRequest",
    "ReturnStatus",
    # Audit logging
    "AuditAction",
    "AuditLog",
    # Webhooks (outbound)
    "DeliveryStatus",
    "WebhookDelivery",
    "WebhookEventType",
    "WebhookSubscription",
    # Webhook Events (inbound)
    "WebhookDeadLetter",
    "WebhookEvent",
    "WebhookEventSource",
    "WebhookEventStatus",
    # Multi-tenancy
    "Tenant",
    "TenantModule",
    "User",
    "UserTenant",
    "UserRole",
    # Platform admin
    "PlatformAdminAuditLog",
    "PlatformSetting",
]
