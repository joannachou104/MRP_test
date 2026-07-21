"""各模組批次匯入邏輯:商品/BOM/通路預測採「新增」「更新」雙介面;
每日庫存採單一介面(方案 B,見 2.7.1);銷貨/銷退為持續累積交易表。

所有匯入皆採「不中斷整批」策略:錯誤列記錄於 import_log.error_detail(JSON),
其餘正常列照常寫入。
"""
import json
import uuid
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app import models

TW_TZ = timezone(timedelta(hours=8))


def new_batch_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(TW_TZ).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"


def today_tw() -> date:
    return datetime.now(TW_TZ).date()


def create_import_log(
    db: Session,
    batch_id: str,
    import_type: str,
    file_name: str,
    imported_by: str,
    success_count: int,
    errors: list[dict],
) -> models.ImportLog:
    log = models.ImportLog(
        batch_id=batch_id,
        import_type=import_type,
        file_name=file_name,
        imported_by=imported_by,
        imported_at=datetime.now(TW_TZ),
        success_count=success_count,
        error_count=len(errors),
        error_detail=json.dumps(errors, ensure_ascii=False) if errors else None,
    )
    db.add(log)
    return log


# ---------------------------------------------------------------------------
# 商品匯入
# ---------------------------------------------------------------------------
PRODUCT_FIELDS = [
    "product_name", "unit", "category", "is_composite", "stock_nature",
    "stock_planning", "lead_time_days", "lead_time_type", "safety_stock_qty",
    "supplier_id", "processing_plant_id", "status",
]


def _coerce_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "y", "是")


def import_products(
    db: Session, rows: list[dict], mode: str, file_name: str, imported_by: str
) -> models.ImportLog:
    """mode: 'create' | 'update'"""
    errors = []
    success_count = 0

    for idx, row in enumerate(rows, start=1):
        product_id = str(row.get("product_id", "")).strip()
        if not product_id:
            errors.append({"row": idx, "error": "product_id 為必填"})
            continue

        existing = db.get(models.ProductMaster, product_id)
        if mode == "create":
            if existing is not None:
                errors.append({"row": idx, "product_id": product_id, "error": "商品編號已存在,無法新增"})
                continue
            try:
                product = models.ProductMaster(
                    product_id=product_id,
                    product_name=row.get("product_name", ""),
                    unit=row.get("unit", ""),
                    category=row.get("category", ""),
                    is_composite=_coerce_bool(row.get("is_composite", False)),
                    stock_nature=row.get("stock_nature", "normal"),
                    stock_planning=row.get("stock_planning", "active"),
                    lead_time_days=int(row.get("lead_time_days") or 0),
                    lead_time_type=row.get("lead_time_type", "procurement"),
                    safety_stock_qty=float(row.get("safety_stock_qty") or 0),
                    supplier_id=row.get("supplier_id") or None,
                    processing_plant_id=row.get("processing_plant_id") or None,
                    status=row.get("status", "active"),
                    updated_by=imported_by,
                )
                db.add(product)
                success_count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({"row": idx, "product_id": product_id, "error": str(exc)})
        else:  # update
            if existing is None:
                errors.append({"row": idx, "product_id": product_id, "error": "找不到既有商品資料,無法更新"})
                continue
            try:
                for field in PRODUCT_FIELDS:
                    if field in row and row[field] not in (None, ""):
                        value = row[field]
                        if field == "is_composite":
                            value = _coerce_bool(value)
                        elif field == "lead_time_days":
                            value = int(value)
                        elif field == "safety_stock_qty":
                            value = float(value)
                        setattr(existing, field, value)
                existing.updated_by = imported_by
                existing.updated_at = datetime.now(TW_TZ)
                success_count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({"row": idx, "product_id": product_id, "error": str(exc)})

    batch_id = new_batch_id("PROD")
    log = create_import_log(db, batch_id, "product", file_name, imported_by, success_count, errors)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# BOM 匯入
# ---------------------------------------------------------------------------
def import_bom(db: Session, rows: list[dict], mode: str, file_name: str, imported_by: str) -> models.ImportLog:
    errors = []
    success_count = 0

    for idx, row in enumerate(rows, start=1):
        parent_id = str(row.get("parent_product_id", "")).strip()
        child_id = str(row.get("child_product_id", "")).strip()
        if not parent_id or not child_id:
            errors.append({"row": idx, "error": "parent_product_id / child_product_id 為必填"})
            continue

        existing = (
            db.query(models.Bom)
            .filter(models.Bom.parent_product_id == parent_id, models.Bom.child_product_id == child_id)
            .first()
        )
        try:
            qty = float(row.get("quantity_per_unit") or 0)
        except Exception:  # noqa: BLE001
            errors.append({"row": idx, "error": "quantity_per_unit 非數值"})
            continue

        if mode == "create":
            if existing is not None:
                errors.append({"row": idx, "error": f"BOM 關係 {parent_id}->{child_id} 已存在,無法新增"})
                continue
            if db.get(models.ProductMaster, parent_id) is None or db.get(models.ProductMaster, child_id) is None:
                errors.append({"row": idx, "error": "parent/child 商品編號不存在於商品主檔"})
                continue
            db.add(models.Bom(parent_product_id=parent_id, child_product_id=child_id, quantity_per_unit=qty))
            success_count += 1
        else:
            if existing is None:
                errors.append({"row": idx, "error": f"找不到 BOM 關係 {parent_id}->{child_id},無法更新"})
                continue
            existing.quantity_per_unit = qty
            existing.updated_at = datetime.now(TW_TZ)
            success_count += 1

    batch_id = new_batch_id("BOM")
    log = create_import_log(db, batch_id, "bom", file_name, imported_by, success_count, errors)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# 通路預測匯入
# ---------------------------------------------------------------------------
def import_channel_forecast(
    db: Session, rows: list[dict], mode: str, file_name: str, imported_by: str
) -> models.ImportLog:
    errors = []
    success_count = 0
    batch_id = new_batch_id("CHFC")

    for idx, row in enumerate(rows, start=1):
        channel_id = str(row.get("channel_id", "")).strip()
        product_id = str(row.get("product_id", "")).strip()
        period_type = str(row.get("period_type", "")).strip()
        period_value = str(row.get("period_value", "")).strip()
        if not all([channel_id, product_id, period_type, period_value]):
            errors.append({"row": idx, "error": "channel_id/product_id/period_type/period_value 為必填"})
            continue
        if db.get(models.SalesChannel, channel_id) is None:
            errors.append({"row": idx, "error": f"通路 {channel_id} 不存在"})
            continue
        if db.get(models.ProductMaster, product_id) is None:
            errors.append({"row": idx, "error": f"商品 {product_id} 不存在"})
            continue
        try:
            qty = float(row.get("forecast_qty") or 0)
        except Exception:  # noqa: BLE001
            errors.append({"row": idx, "error": "forecast_qty 非數值"})
            continue

        existing = (
            db.query(models.ChannelForecastExternal)
            .filter(
                models.ChannelForecastExternal.channel_id == channel_id,
                models.ChannelForecastExternal.product_id == product_id,
                models.ChannelForecastExternal.period_type == period_type,
                models.ChannelForecastExternal.period_value == period_value,
            )
            .first()
        )
        if mode == "create":
            if existing is not None:
                errors.append({"row": idx, "error": "此通路/商品/期間之預測已存在,無法新增"})
                continue
            db.add(
                models.ChannelForecastExternal(
                    channel_id=channel_id,
                    product_id=product_id,
                    period_type=period_type,
                    period_value=period_value,
                    forecast_qty=qty,
                    import_batch_id=batch_id,
                )
            )
            success_count += 1
        else:
            if existing is None:
                errors.append({"row": idx, "error": "找不到既有預測資料,無法更新"})
                continue
            existing.forecast_qty = qty
            existing.import_batch_id = batch_id
            success_count += 1

    log = create_import_log(db, batch_id, "channel_forecast", file_name, imported_by, success_count, errors)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# 銷貨/銷退交易匯入(持續累積,無新增/更新區分)
# ---------------------------------------------------------------------------
def import_sales_transactions(
    db: Session, rows: list[dict], is_bulk_initial: bool, file_name: str, imported_by: str
) -> models.ImportLog:
    errors = []
    success_count = 0
    import_type = "sales_bulk" if is_bulk_initial else "sales_daily_incremental"
    batch_id = new_batch_id("SALE")

    for idx, row in enumerate(rows, start=1):
        product_id = str(row.get("product_id", "")).strip()
        channel_id = str(row.get("channel_id", "")).strip()
        doc_type = str(row.get("doc_type", "sale")).strip()
        try:
            doc_date = row["doc_date"]
            if isinstance(doc_date, str):
                doc_date = datetime.strptime(doc_date[:10], "%Y-%m-%d").date()
            elif isinstance(doc_date, datetime):
                doc_date = doc_date.date()
            qty = float(row.get("quantity") or 0)
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "error": f"日期或數量格式錯誤: {exc}"})
            continue

        if db.get(models.ProductMaster, product_id) is None:
            errors.append({"row": idx, "error": f"商品 {product_id} 不存在"})
            continue
        if db.get(models.SalesChannel, channel_id) is None:
            errors.append({"row": idx, "error": f"通路 {channel_id} 不存在"})
            continue

        db.add(
            models.SalesTransaction(
                doc_no=row.get("doc_no"),
                doc_date=doc_date,
                product_id=product_id,
                channel_id=channel_id,
                quantity=qty,
                doc_type="return" if doc_type == "return" else "sale",
                import_batch_id=batch_id,
            )
        )
        success_count += 1

    log = create_import_log(db, batch_id, import_type, file_name, imported_by, success_count, errors)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# 每日庫存匯入(2.7.1 詳細規格,方案 B)
# ---------------------------------------------------------------------------
def import_inventory_daily(
    db: Session, rows: list[dict], file_name: str, imported_by: str
) -> dict:
    snapshot_date = today_tw()
    errors = []
    success_count = 0
    batch_id = new_batch_id("INV")

    already_has_records_today = (
        db.query(models.InventoryDaily)
        .filter(models.InventoryDaily.snapshot_date == snapshot_date)
        .first()
        is not None
    )
    is_first_upload_of_day = not already_has_records_today

    uploaded_product_ids: set[str] = set()

    for idx, row in enumerate(rows, start=1):
        product_id = str(row.get("product_id", "")).strip()
        if not product_id:
            errors.append({"row": idx, "error": "product_id 為必填"})
            continue
        if db.get(models.ProductMaster, product_id) is None:
            errors.append({"row": idx, "product_id": product_id, "error": "商品編號比對不到商品主檔資料"})
            continue
        try:
            qty = float(row.get("quantity"))
            if qty < 0:
                raise ValueError("quantity 需 >= 0")
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "product_id": product_id, "error": f"quantity 錯誤: {exc}"})
            continue

        existing = (
            db.query(models.InventoryDaily)
            .filter(
                models.InventoryDaily.snapshot_date == snapshot_date,
                models.InventoryDaily.product_id == product_id,
            )
            .first()
        )
        if existing is not None:
            existing.quantity = qty
            existing.import_batch_id = batch_id
        else:
            db.add(
                models.InventoryDaily(
                    snapshot_date=snapshot_date,
                    product_id=product_id,
                    quantity=qty,
                    import_batch_id=batch_id,
                )
            )
        uploaded_product_ids.add(product_id)
        success_count += 1

    if is_first_upload_of_day:
        # 當天第一次上傳:建立完整快照基準,active+normal 商品未列出者一律補 0
        all_active_normal = (
            db.query(models.ProductMaster)
            .filter(models.ProductMaster.status == "active", models.ProductMaster.stock_nature == "normal")
            .all()
        )
        for product in all_active_normal:
            if product.product_id in uploaded_product_ids:
                continue
            db.add(
                models.InventoryDaily(
                    snapshot_date=snapshot_date,
                    product_id=product.product_id,
                    quantity=0,
                    import_batch_id=batch_id,
                )
            )

    log = create_import_log(db, batch_id, "inventory_daily", file_name, imported_by, success_count, errors)
    db.commit()
    db.refresh(log)

    return {
        "log": log,
        "snapshot_date": snapshot_date.isoformat(),
        "is_first_upload_of_day": is_first_upload_of_day,
        "message": f"本次上傳已計入 {snapshot_date.month}月{snapshot_date.day}日庫存快照",
    }
