"""Pydantic data models for synthetic supply chain graph entities and relationships."""

from pydantic import BaseModel, Field


class Country(BaseModel):
    """Represents a country node with geopolitical risk index."""

    code: str = Field(..., description="ISO 3166-1 alpha-2 code")
    name: str = Field(..., description="Country name")
    region: str = Field(..., description="Geographic region")
    risk_index: float = Field(..., ge=0.0, le=1.0, description="Risk index between 0.0 and 1.0")


class Port(BaseModel):
    """Represents a maritime shipping port node."""

    id: str = Field(..., description="Unique port identifier")
    name: str = Field(..., description="Port name")
    country_code: str = Field(..., description="ISO country code")
    un_locode: str = Field(..., description="UN Location Code")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    throughput_teu_annual: int = Field(..., ge=0, description="Annual TEU throughput")


class Supplier(BaseModel):
    """Represents a supply chain vendor node."""

    id: str = Field(..., description="Unique supplier identifier")
    name: str = Field(..., description="Supplier company name")
    country_code: str = Field(..., description="ISO country code")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Reliability score 0 to 1")
    lead_time_days: int = Field(..., ge=1, description="Average lead time in days")
    tier: int = Field(..., ge=1, le=3, description="Supply chain tier: 1, 2, or 3")


class Facility(BaseModel):
    """Represents a manufacturing or distribution site operated by a supplier."""

    id: str = Field(..., description="Unique facility identifier")
    name: str = Field(..., description="Facility name")
    supplier_id: str = Field(..., description="ID of operating supplier")
    country_code: str = Field(..., description="ISO country code")
    facility_type: str = Field(..., description="factory, warehouse, or dc")
    capacity_units: int = Field(..., ge=0, description="Annual capacity in units")
    lat: float = Field(..., description="Latitude coordinate")
    lon: float = Field(..., description="Longitude coordinate")


class Component(BaseModel):
    """Represents a bill of materials component part node."""

    id: str = Field(..., description="Unique component identifier")
    name: str = Field(..., description="Component name")
    category: str = Field(..., description="Component category (e.g. Memory, Processor, Display)")
    unit_cost_usd: float = Field(..., ge=0.0, description="Unit cost in USD")
    lead_time_days: int = Field(..., ge=1, description="Lead time in days")
    is_sole_sourced: bool = Field(..., description="Whether component has a single supplier")


class Product(BaseModel):
    """Represents an end product manufactured and sold by the OEM."""

    id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Stock keeping unit code")
    family: str = Field(..., description="Product family category")
    revenue_usd_annual: float = Field(..., ge=0.0, description="Annual revenue generated in USD")
    margin_pct: float = Field(..., ge=0.0, le=100.0, description="Gross profit margin percentage")


class Customer(BaseModel):
    """Represents an enterprise or commercial customer node."""

    id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer enterprise name")
    country_code: str = Field(..., description="ISO country code")
    annual_revenue_usd: float = Field(..., ge=0.0, description="Annual account revenue in USD")
    segment: str = Field(..., description="Business segment")


class SupplierOperatesFacility(BaseModel):
    """Represents OPERATES relationship from Supplier to Facility."""

    supplier_id: str
    facility_id: str
    since_year: int


class SupplierProducesComponent(BaseModel):
    """Represents PRODUCES relationship from Supplier to Component."""

    supplier_id: str
    component_id: str
    annual_volume: int
    is_primary: bool


class ComponentPartOfProduct(BaseModel):
    """Represents PART_OF relationship from Component to Product."""

    component_id: str
    product_id: str
    quantity: int
    is_critical: bool


class SupplierShipsViaPort(BaseModel):
    """Represents SHIPS_VIA relationship from Supplier to Port."""

    supplier_id: str
    port_id: str
    primary: bool
    avg_transit_days: int


class SupplierAlternativeFor(BaseModel):
    """Represents ALTERNATIVE_FOR relationship between Suppliers."""

    supplier_id: str
    alternative_supplier_id: str
    component_id: str
    qualification_status: str


class FacilityShipsToCustomer(BaseModel):
    """Represents SHIPS_TO relationship from Facility to Customer."""

    facility_id: str
    customer_id: str
    annual_volume_units: int
