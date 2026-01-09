"""Material type schemas for API requests and responses."""

from pydantic import BaseModel, ConfigDict, Field


class MaterialTypeBase(BaseModel):
    """Base schema for material types."""

    code: str = Field(..., max_length=20, description="Short code (e.g., PLA, PETG)")
    name: str = Field(..., max_length=100, description="Full material name")
    description: str | None = Field(None, description="Material properties and uses")
    typical_density: float | None = Field(None, ge=0, description="Typical density in g/cm³")
    typical_cost_per_kg: float | None = Field(None, ge=0, description="Typical cost per kg")
    min_temp: int | None = Field(None, ge=0, le=500, description="Min printing temp (°C)")
    max_temp: int | None = Field(None, ge=0, le=500, description="Max printing temp (°C)")
    bed_temp: int | None = Field(None, ge=0, le=200, description="Bed temperature (°C)")
    is_active: bool = Field(True, description="Whether material type is active")


class MaterialTypeCreate(MaterialTypeBase):
    """Schema for creating a new material type."""

    pass


class MaterialTypeUpdate(BaseModel):
    """Schema for updating a material type."""

    name: str | None = None
    description: str | None = None
    typical_density: float | None = None
    typical_cost_per_kg: float | None = None
    min_temp: int | None = None
    max_temp: int | None = None
    bed_temp: int | None = None
    is_active: bool | None = None


class MaterialTypeResponse(MaterialTypeBase):
    """Schema for material type responses."""

    id: str
    model_config = ConfigDict(from_attributes=True)
