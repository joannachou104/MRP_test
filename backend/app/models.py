from datetime import datetime, date
from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Numeric,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# 2.1 商品主檔 product_master
# ---------------------------------------------------------------------------
class ProductMaster(Base):
    __tablename__ = "product_master"

    product_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(10), default="")
    category: Mapped[str] = mapped_column(String(50), default="")
    is_composite: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_nature: Mapped[str] = mapped_column(String(20), default="normal")  # normal | non_stock
    stock_planning: Mapped[str] = mapped_column(String(20), default="active")  # active | manual
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)
    lead_time_type: Mapped[str] = mapped_column(String(20), default="procurement")  # procurement|processing|qc
    safety_stock_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    supplier_id: Mapped[str | None] = mapped_column(String(30), ForeignKey("supplier.supplier_id"), nullable=True)
    processing_plant_id: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("processing_plant.plant_id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | inactive
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by: Mapped[str] = mapped_column(String(50), default="")


# ---------------------------------------------------------------------------
# 2.2 BOM 表
# ---------------------------------------------------------------------------
class Bom(Base):
    __tablename__ = "bom"

    bom_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    child_product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    quantity_per_unit: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("parent_product_id", "child_product_id", name="uq_bom_parent_child"),)


# ---------------------------------------------------------------------------
# 2.3 供應商主檔
# ---------------------------------------------------------------------------
class Supplier(Base):
    __tablename__ = "supplier"

    supplier_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(100))
    min_order_qty: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)


# ---------------------------------------------------------------------------
# 2.4 通路主檔
# ---------------------------------------------------------------------------
class SalesChannel(Base):
    __tablename__ = "sales_channel"

    channel_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    channel_name: Mapped[str] = mapped_column(String(50))
    forecast_source: Mapped[str] = mapped_column(String(30))  # external_quarterly|external_monthly|internal_calculated


# ---------------------------------------------------------------------------
# 2.5 通路外部預測表
# ---------------------------------------------------------------------------
class ChannelForecastExternal(Base):
    __tablename__ = "channel_forecast_external"

    forecast_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(30), ForeignKey("sales_channel.channel_id"))
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    period_type: Mapped[str] = mapped_column(String(10))  # quarter | month
    period_value: Mapped[str] = mapped_column(String(10))  # 2026-Q3 or 2026-07
    forecast_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    import_batch_id: Mapped[str | None] = mapped_column(String(30), nullable=True)


# ---------------------------------------------------------------------------
# 2.6 銷貨/銷退交易表
# ---------------------------------------------------------------------------
class SalesTransaction(Base):
    __tablename__ = "sales_transaction"

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    doc_date: Mapped[date] = mapped_column(Date)
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    channel_id: Mapped[str] = mapped_column(String(30), ForeignKey("sales_channel.channel_id"))
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    doc_type: Mapped[str] = mapped_column(String(10))  # sale | return
    import_batch_id: Mapped[str | None] = mapped_column(String(30), nullable=True)


# ---------------------------------------------------------------------------
# 2.7 每日庫存快照表
# ---------------------------------------------------------------------------
class InventoryDaily(Base):
    __tablename__ = "inventory_daily"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date)
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    import_batch_id: Mapped[str | None] = mapped_column(String(30), nullable=True)

    __table_args__ = (UniqueConstraint("snapshot_date", "product_id", name="uq_inventory_date_product"),)


# ---------------------------------------------------------------------------
# 2.8 MRP 運算結果表
# ---------------------------------------------------------------------------
class MrpResult(Base):
    __tablename__ = "mrp_result"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_date: Mapped[date] = mapped_column(Date)
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    forecast_demand: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    current_stock: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    sellable_days: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    net_requirement: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    suggested_order_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    suggested_order_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    trigger_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)  # lead_time_breach|below_safety_stock|both
    recommendation_type: Mapped[str] = mapped_column(String(20), default="active")  # active | reference
    review_status: Mapped[str] = mapped_column(String(20), default="unreviewed")  # unreviewed | ignored
    reviewed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# 2.9 匯入批次紀錄表
# ---------------------------------------------------------------------------
class ImportLog(Base):
    __tablename__ = "import_log"

    batch_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    import_type: Mapped[str] = mapped_column(String(30))
    file_name: Mapped[str] = mapped_column(String(200), default="")
    imported_by: Mapped[str] = mapped_column(String(50), default="")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


# ---------------------------------------------------------------------------
# 2.10 採購在途紀錄表
# ---------------------------------------------------------------------------
class ProcurementPending(Base):
    __tablename__ = "procurement_pending"

    pending_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    source_result_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mrp_result.result_id"), nullable=True)
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    received_qty: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | arrived
    registered_by: Mapped[str] = mapped_column(String(50), default="")
    arrived_confirmed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    arrived_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# 2.11 商品缺口忽略設定表
# ---------------------------------------------------------------------------
class MrpIgnore(Base):
    __tablename__ = "mrp_ignore"

    ignore_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"), unique=True)
    ignored_by: Mapped[str] = mapped_column(String(50), default="")
    ignored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)


# ---------------------------------------------------------------------------
# 2.12 加工廠主檔
# ---------------------------------------------------------------------------
class ProcessingPlant(Base):
    __tablename__ = "processing_plant"

    plant_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    plant_name: Mapped[str] = mapped_column(String(100))
    contact_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")


# ---------------------------------------------------------------------------
# 2.13 委外加工排程表
# ---------------------------------------------------------------------------
class ProcessingOrder(Base):
    __tablename__ = "processing_order"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    plant_id: Mapped[str] = mapped_column(String(30), ForeignKey("processing_plant.plant_id"))
    planned_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    required_date: Mapped[date] = mapped_column(Date)
    import_batch_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# 2.14 原料配送批次表
# ---------------------------------------------------------------------------
class MaterialDistributionBatch(Base):
    __tablename__ = "material_distribution_batch"

    batch_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    run_date: Mapped[date] = mapped_column(Date)
    material_product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    source_type: Mapped[str] = mapped_column(String(30))  # inventory_transfer | direct_procurement
    source_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_available_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    remaining_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    remaining_disposition: Mapped[str] = mapped_column(String(30), default="unconfirmed")
    disposition_confirmed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disposition_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# 2.15 原料配送明細表
# ---------------------------------------------------------------------------
class MaterialDistributionDetail(Base):
    __tablename__ = "material_distribution_detail"

    detail_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(30), ForeignKey("material_distribution_batch.batch_id"))
    target_product_id: Mapped[str] = mapped_column(String(30), ForeignKey("product_master.product_id"))
    target_plant_id: Mapped[str] = mapped_column(String(30), ForeignKey("processing_plant.plant_id"))
    required_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    allocated_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    shortage_qty: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    priority_rank: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# 系統設定/權限 — 簡易使用者表(本機測試用,非正式帳密系統)
# ---------------------------------------------------------------------------
class AppUser(Base):
    __tablename__ = "app_user"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(20))  # admin | procurement | viewer

    __table_args__ = ()


class ChangeLog(Base):
    """異動紀錄查詢(交接用) — 記錄關鍵操作供追溯"""

    __tablename__ = "change_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(50))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    operated_by: Mapped[str] = mapped_column(String(50), default="")
    operated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
