from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_procurement_permission, CurrentUser
from app.services import changelog_service

router = APIRouter(prefix="/api/ignore", tags=["忽略清單複核"])


@router.get("", response_model=list[schemas.MrpIgnoreRead])
def list_ignored(db: Session = Depends(get_db)):
    return db.query(models.MrpIgnore).order_by(models.MrpIgnore.ignored_at.desc()).all()


@router.post("", response_model=schemas.MrpIgnoreRead)
def add_ignore(
    payload: schemas.MrpIgnoreCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_procurement_permission(user)
    if db.get(models.ProductMaster, payload.product_id) is None:
        raise HTTPException(400, "商品不存在")
    existing = db.query(models.MrpIgnore).filter(models.MrpIgnore.product_id == payload.product_id).first()
    if existing is not None:
        raise HTTPException(400, "此商品已在忽略清單中")
    row = models.MrpIgnore(product_id=payload.product_id, note=payload.note, ignored_by=user.name)
    db.add(row)

    latest_result = (
        db.query(models.MrpResult)
        .filter(models.MrpResult.product_id == payload.product_id)
        .order_by(models.MrpResult.run_date.desc(), models.MrpResult.result_id.desc())
        .first()
    )
    if latest_result is not None:
        latest_result.review_status = "ignored"
        latest_result.reviewed_by = user.name

    changelog_service.log(db, "add_ignore", "mrp_ignore", payload.product_id, user.name, payload.note or "")
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{ignore_id}")
def remove_ignore(
    ignore_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    require_procurement_permission(user)
    row = db.get(models.MrpIgnore, ignore_id)
    if row is None:
        raise HTTPException(404, "忽略設定不存在")

    latest_result = (
        db.query(models.MrpResult)
        .filter(models.MrpResult.product_id == row.product_id)
        .order_by(models.MrpResult.run_date.desc(), models.MrpResult.result_id.desc())
        .first()
    )
    if latest_result is not None and latest_result.review_status == "ignored":
        latest_result.review_status = "unreviewed"

    changelog_service.log(db, "remove_ignore", "mrp_ignore", row.product_id, user.name)
    db.delete(row)
    db.commit()
    return {"ok": True}
