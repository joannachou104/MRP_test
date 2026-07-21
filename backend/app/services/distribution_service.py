"""3.7 配送清單運算邏輯:同一下層節點(原料或成品)被多個上層節點(成品或組合品)
共用,依交期優先順序分配可分配總量給各加工廠/包裝廠。
"""
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app import models
from app.services import bom_service, import_service

TW_TZ = timezone(timedelta(hours=8))


class DistributionError(Exception):
    pass


def generate_distribution(
    db: Session,
    material_product_id: str,
    total_available_qty: float,
    source_type: str,
    source_reference: str | None,
    created_by: str,
) -> models.MaterialDistributionBatch:
    material = db.get(models.ProductMaster, material_product_id)
    if material is None:
        raise DistributionError(f"商品 {material_product_id} 不存在")

    # 「成品→組合品」情境(下層節點本身是成品,is_composite=True 代表它有自己的 BOM
    # 由原料組成):只能是庫存轉移,不會有原料商直送包裝廠的情況
    if material.is_composite and source_type == "direct_procurement":
        raise DistributionError("成品→組合品情境僅能選擇「庫存轉移」,不適用「原料商直送」")

    parent_bom_rows = bom_service.get_parents(db, material_product_id)
    parent_ids = [row.parent_product_id for row in parent_bom_rows]
    qty_per_unit_map = {row.parent_product_id: float(row.quantity_per_unit) for row in parent_bom_rows}

    processing_orders = (
        db.query(models.ProcessingOrder).filter(models.ProcessingOrder.product_id.in_(parent_ids)).all()
        if parent_ids
        else []
    )

    demand_rows = []
    for po in processing_orders:
        qty_per_unit = qty_per_unit_map.get(po.product_id)
        if qty_per_unit is None:
            continue
        required_qty = qty_per_unit * float(po.planned_qty)
        demand_rows.append(
            {
                "target_product_id": po.product_id,
                "target_plant_id": po.plant_id,
                "required_date": po.required_date,
                "required_qty": required_qty,
            }
        )

    demand_rows.sort(key=lambda r: r["required_date"])

    batch_id = import_service.new_batch_id("DIST")
    remaining_pool = float(total_available_qty)
    details: list[models.MaterialDistributionDetail] = []

    for rank, row in enumerate(demand_rows, start=1):
        allocated = min(row["required_qty"], max(remaining_pool, 0))
        shortage = row["required_qty"] - allocated
        remaining_pool -= allocated
        details.append(
            models.MaterialDistributionDetail(
                batch_id=batch_id,
                target_product_id=row["target_product_id"],
                target_plant_id=row["target_plant_id"],
                required_qty=row["required_qty"],
                allocated_qty=allocated,
                shortage_qty=max(shortage, 0),
                priority_rank=rank,
            )
        )

    batch = models.MaterialDistributionBatch(
        batch_id=batch_id,
        run_date=date.today(),
        material_product_id=material_product_id,
        source_type=source_type,
        source_reference=source_reference,
        total_available_qty=total_available_qty,
        remaining_qty=max(remaining_pool, 0),
        remaining_disposition="unconfirmed",
        created_by=created_by,
        created_at=datetime.now(TW_TZ),
    )
    db.add(batch)
    for d in details:
        db.add(d)
    db.commit()
    db.refresh(batch)
    return batch


def get_latest_stock_hint(db: Session, product_id: str) -> float | None:
    """多段串鏈:輸入第二段(成品→組合品)可分配總量時,提示該成品目前庫存作為參考上限。"""
    row = (
        db.query(models.InventoryDaily)
        .filter(models.InventoryDaily.product_id == product_id)
        .order_by(models.InventoryDaily.snapshot_date.desc())
        .first()
    )
    return float(row.quantity) if row else None
