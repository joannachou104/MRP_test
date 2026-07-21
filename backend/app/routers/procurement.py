from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_procurement_permission, CurrentUser
from app.services import changelog_service

router = APIRouter(prefix="/api/procurement", tags=["採購建議"])


@router.get("/pending", response_model=list[schemas.ProcurementPendingRead])
def list_pending(
    product_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ProcurementPending)
    if product_id:
        query = query.filter(models.ProcurementPending.product_id == product_id)
    if status:
        query = query.filter(models.ProcurementPending.status == status)
    return query.order_by(models.ProcurementPending.updated_at.desc()).all()


@router.post("/pending", response_model=schemas.ProcurementPendingRead)
def register_pending(
    payload: schemas.ProcurementPendingCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_procurement_permission(user)
    if db.get(models.ProductMaster, payload.product_id) is None:
        raise HTTPException(400, "商品不存在")
    row = models.ProcurementPending(
        **payload.model_dump(),
        status="pending",
        registered_by=user.name,
    )
    db.add(row)
    db.flush()
    changelog_service.log(
        db, "register_pending", "procurement_pending", row.pending_id, user.name,
        f"product={payload.product_id} expected_qty={payload.expected_qty}",
    )
    db.commit()
    db.refresh(row)
    return row


@router.post("/pending/{pending_id}/confirm-arrival", response_model=list[schemas.ProcurementPendingRead])
def confirm_arrival(
    pending_id: int,
    payload: schemas.ProcurementArrivalConfirm,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_procurement_permission(user)
    row = db.get(models.ProcurementPending, pending_id)
    if row is None:
        raise HTTPException(404, "在途紀錄不存在")
    if row.status != "pending":
        raise HTTPException(400, "此紀錄已非待到貨狀態")

    received_qty = payload.received_qty
    row.received_qty = received_qty
    row.status = "arrived"
    row.arrived_confirmed_by = user.name
    row.arrived_confirmed_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()

    created_rows = [row]

    shortfall = float(row.expected_qty) - received_qty
    if shortfall > 0:
        # 支援部分到貨:剩餘量自動產生新的一筆待到貨記錄,沿用同一 source_result_id
        new_row = models.ProcurementPending(
            product_id=row.product_id,
            source_result_id=row.source_result_id,
            order_date=row.order_date,
            expected_arrival_date=row.expected_arrival_date,
            expected_qty=shortfall,
            status="pending",
            registered_by=row.registered_by,
        )
        db.add(new_row)
        created_rows.append(new_row)

    changelog_service.log(
        db, "confirm_arrival", "procurement_pending", pending_id, user.name,
        f"received_qty={received_qty} shortfall={max(shortfall, 0)}",
    )
    db.commit()
    for r in created_rows:
        db.refresh(r)
    return created_rows


@router.delete("/pending/{pending_id}")
def cancel_pending(
    pending_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_procurement_permission(user)
    row = db.get(models.ProcurementPending, pending_id)
    if row is None:
        raise HTTPException(404, "在途紀錄不存在")
    changelog_service.log(
        db, "cancel_pending", "procurement_pending", pending_id, user.name,
        f"product={row.product_id} expected_qty={row.expected_qty}",
    )
    db.delete(row)
    db.commit()
    return {"ok": True}
