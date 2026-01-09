"""Model file for 3D model file tracking (STL, 3MF, gcode, etc.)."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.user import User


class ModelFileType(str, Enum):
    """Types of 3D model files."""

    SOURCE_STL = "source_stl"  # Original STL file from designer
    SOURCE_3MF = "source_3mf"  # Original 3MF file from designer
    SLICER_PROJECT = "slicer_project"  # Slicer project file with settings
    GCODE = "gcode"  # Pre-sliced gcode ready to print
    PLATE_LAYOUT = "plate_layout"  # Plate arrangement file


class ModelFile(Base, UUIDMixin, TimestampMixin):
    """
    ModelFile tracks 3D model files associated with a Model.

    Supports multiple files per model (multi-part models), versioning,
    and different file types (source files, slicer projects, gcode).
    """

    __tablename__ = "model_files"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant this file belongs to",
    )

    # Model reference
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="3D model this file is associated with",
    )

    # File type categorization
    file_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="File type: source_stl, source_3mf, slicer_project, gcode, plate_layout",
    )

    # File storage
    file_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URL or path to the stored file",
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename as uploaded",
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )

    content_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="MIME content type (e.g., model/stl, model/3mf)",
    )

    # Multi-part model support
    part_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Part name for multi-part models (e.g., 'body', 'wings', 'base')",
    )

    # Versioning
    version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Version identifier (e.g., 'v2.1', '2024-01-15')",
    )

    # Primary file flag
    is_primary: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="Whether this is the primary/default file for the model",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User notes about the file (e.g., slicer settings, print tips)",
    )

    # Audit trail
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When the file was uploaded",
    )

    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who uploaded the file",
    )

    # Relationships
    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="files",
        lazy="select",
    )

    uploaded_by: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ModelFile(id={self.id}, model_id={self.model_id}, type={self.file_type}, filename={self.original_filename})>"
