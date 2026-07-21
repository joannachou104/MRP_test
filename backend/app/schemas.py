from datetime import date, datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# 商品主檔
# ---------------------------------------------------------------------------
class ProductBase(BaseModel):
    product_name: str
    unit: str = ""
    category: str = ""
    is_composite: bool = False
    stock_nature: Literal["normal", "non_stock"] = "normal"
    stock_planning: Literal["active", "manual"] = "active"
    lead_time_days: int = 0
    lead_time_type: Literal["procurement", "processing", "qc"] = "procurement"
    safety_stock_qty: float = 0
    supplier_id: Optional[str] = None
    processing_plant_id: Optional[str] = None
    status: Literal["active", "inactive"] = "active"


class ProductCreate(ProductBase):
    product_id: str


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    is_composite: Optional[bool] = None
    stock_nature: Optional[Literal["normal", "non_stock"]] = None
    stock_planning: Optional[Literal["active", "manual"]] = None
    lead_time_days: Optional[int] = None
    lead_time_type: Optional[Literal["procurement", "processing", "qc"]] = None
    safety_stock_qty: Optional[float] = None
    supplier_id: Optional[str] = None
    processing_plant_id: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    created_at: datetime
    updated_at: datetime
    updated_by: str


# ---------------------------------------------------------------------------
# BOM
# ---------------------------------------------------------------------------
class BomCreate(BaseModel):
    parent_product_id: str
    child_product_id: str
    quantity_per_unit: float


class BomRead(BomCreate):
    model_config = ConfigDict(from_attributes=True)
    bom_id: int
    updated_at: datetime


# ---------------------------------------------------------------------------
# 供應商
# ---------------------------------------------------------------------------
class SupplierCreate(BaseModel):
    supplier_id: str
    supplier_name: str
    min_order_qty: Optional[float] = None


class SupplierUpdate(BaseModel):
    supplier_name: Optional[str] = None
    min_order_qty: Optional[float] = None


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    supplier_id: str
    supplier_name: str
    min_order_qty: Optional[float] = None


# ---------------------------------------------------------------------------
# 加工廠
# ---------------------------------------------------------------------------
class PlantCreate(BaseModel):
    plant_id: str
    plant_name: str
    contact_info: Optional[str] = None
    status: Literal["active", "inactive"] = "active"


class PlantUpdate(BaseModel):
    plant_name: Optional[str] = None
    contact_info: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None


class PlantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    plant_id: str
    plant_name: str
    contact_info: Optional[str] = None
    status: str


# ---------------------------------------------------------------------------
# 通路
# ---------------------------------------------------------------------------
class ChannelCreate(BaseModel):
    channel_id: str
    channel_name: str
    forecast_source: Literal["external_quarterly", "external_monthly", "internal_calculated"]


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    channel_id: str
    channel_name: str
    forecast_source: str


class ChannelForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    forecast_id: int
    channel_id: str
    product_id: str
    period_type: str
    period_value: str
    forecast_qty: float
    import_batch_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 銷貨交易 / 庫存快照
# ---------------------------------------------------------------------------
class SalesTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    record_id: int
    doc_no: Optional[str] = None
    doc_date: date
    product_id: str
    channel_id: str
    quantity: float
    doc_type: str
    import_batch_id: Optional[str] = None


class InventoryDailyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    snapshot_id: int
    snapshot_date: date
    product_id: str
    quantity: float
    import_batch_id: Optional[str] = None


# ---------------------------------------------------------------------------
# MRP 結果
# ---------------------------------------------------------------------------
class MrpResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    result_id: int
    run_date: date
    product_id: str
    forecast_demand: float
    current_stock: float
    sellable_days: float
    net_requirement: float
    suggested_order_qty: float
    suggested_order_deadline: Optional[date] = None
    trigger_reason: Optional[str] = None
    recommendation_type: str
    review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# 採購在途
# ---------------------------------------------------------------------------
class ProcurementPendingCreate(BaseModel):
    product_id: str
    source_result_id: Optional[int] = None
    order_date: Optional[date] = None
    expected_arrival_date: Optional[date] = None
    expected_qty: float


class ProcurementArrivalConfirm(BaseModel):
    received_qty: float


class ProcurementPendingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pending_id: int
    product_id: str
    source_result_id: Optional[int] = None
    order_date: Optional[date] = None
    expected_arrival_date: Optional[date] = None
    expected_qty: float
    received_qty: Optional[float] = None
    status: str
    registered_by: str
    arrived_confirmed_by: Optional[str] = None
    arrived_confirmed_at: Optional[datetime] = None
    updated_at: datetime


# ---------------------------------------------------------------------------
# 忽略清單
# ---------------------------------------------------------------------------
class MrpIgnoreCreate(BaseModel):
    product_id: str
    note: Optional[str] = None


class MrpIgnoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ignore_id: int
    product_id: str
    ignored_by: str
    ignored_at: datetime
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# 委外加工排程
# ---------------------------------------------------------------------------
class ProcessingOrderCreate(BaseModel):
    product_id: str
    plant_id: str
    planned_qty: float
    required_date: date


class ProcessingOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order_id: int
    product_id: str
    plant_id: str
    planned_qty: float
    required_date: date
    import_batch_id: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# 原料配送
# ---------------------------------------------------------------------------
class DistributionGenerateRequest(BaseModel):
    material_product_id: str
    total_available_qty: float
    source_type: Literal["inventory_transfer", "direct_procurement"]
    source_reference: Optional[str] = None


class DistributionDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    detail_id: int
    batch_id: str
    target_product_id: str
    target_plant_id: str
    required_qty: float
    allocated_qty: float
    shortage_qty: float
    priority_rank: int


class DistributionBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    batch_id: str
    run_date: date
    material_product_id: str
    source_type: str
    source_reference: Optional[str] = None
    total_available_qty: float
    remaining_qty: float
    remaining_disposition: str
    disposition_confirmed_by: Optional[str] = None
    disposition_confirmed_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    details: list[DistributionDetailRead] = []


class DispositionConfirmRequest(BaseModel):
    disposition: Literal["return_to_warehouse", "keep_at_source"]


# ---------------------------------------------------------------------------
# 匯入紀錄
# ---------------------------------------------------------------------------
class ImportLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    batch_id: str
    import_type: str
    file_name: str
    imported_by: str
    imported_at: datetime
    success_count: int
    error_count: int
    error_detail: Optional[str] = None


# ---------------------------------------------------------------------------
# 使用者/權限
# ---------------------------------------------------------------------------
class AppUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    display_name: str
    role: str


class ChangeLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    log_id: int
    action_type: str
    target_type: str
    target_id: str
    detail: Optional[str] = None
    operated_by: str
    operated_at: datetime
