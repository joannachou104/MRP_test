from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, CurrentUser
from app.services import distribution_service, changelog_service

router = APIRouter(prefix="/api/distribution", tags=["加工配送管理"])


@router.get("", response_model=list[schemas.DistributionBatchRead])
def list_batches(material_product_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.MaterialDistributionBatch)
    if material_product_id:
        query = query.filter(models.MaterialDistributionBatch.material_product_id == material_product_id)
    batches = query.order_by(models.MaterialDistributionBatch.created_at.desc()).all()
    result = []
    for b in batches:
        details = (
            db.query(models.MaterialDistributionDetail)
            .filter(models.MaterialDistributionDetail.batch_id == b.batch_id)
            .order_by(models.MaterialDistributionDetail.priority_rank)
            .all()
        )
        read = schemas.DistributionBatchRead.model_validate(b)
        read.details = [schemas.DistributionDetailRead.model_validate(d) for d in details]
        result.append(read)
    return result


@router.get("/stock-hint/{product_id}")
def stock_hint(product_id: str, db: Session = Depends(get_db)):
    """多段串鏈:輸入第二段(成品→組合品)可分配總量時,提示該成品目前庫存作為參考上限。"""
    qty = distribution_service.get_latest_stock_hint(db, product_id)
    return {"product_id": product_id, "current_stock": qty}


@router.post("/generate", response_model=schemas.DistributionBatchRead)
def generate_distribution(
    payload: schemas.DistributionGenerateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    try:
        batch = distribution_service.generate_distribution(
            db,
            payload.material_product_id,
            payload.total_available_qty,
            payload.source_type,
            payload.source_reference,
            user.name,
        )
    except distribution_service.DistributionError as exc:
        raise HTTPException(400, str(exc)) from exc

    changelog_service.log(
        db, "generate_distribution", "material_distribution_batch", batch.batch_id, user.name,
        f"material={payload.material_product_id} qty={payload.total_available_qty}",
    )
    db.commit()

    details = (
        db.query(models.MaterialDistributionDetail)
        .filter(models.MaterialDistributionDetail.batch_id == batch.batch_id)
        .order_by(models.MaterialDistributionDetail.priority_rank)
        .all()
    )
    read = schemas.DistributionBatchRead.model_validate(batch)
    read.details = [schemas.DistributionDetailRead.model_validate(d) for d in details]
    return read


@router.post("/{batch_id}/confirm-disposition", response_model=schemas.DistributionBatchRead)
def confirm_disposition(
    batch_id: str,
    payload: schemas.DispositionConfirmRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    batch = db.get(models.MaterialDistributionBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "配送批次不存在")
    if batch.remaining_qty <= 0:
        raise HTTPException(400, "此批次無剩餘量需確認去向")
    batch.remaining_disposition = payload.disposition
    batch.disposition_confirmed_by = user.name
    batch.disposition_confirmed_at = datetime.utcnow()
    changelog_service.log(
        db, "confirm_disposition", "material_distribution_batch", batch_id, user.name, payload.disposition
    )
    db.commit()
    db.refresh(batch)

    details = (
        db.query(models.MaterialDistributionDetail)
        .filter(models.MaterialDistributionDetail.batch_id == batch.batch_id)
        .order_by(models.MaterialDistributionDetail.priority_rank)
        .all()
    )
    read = schemas.DistributionBatchRead.model_validate(batch)
    read.details = [schemas.DistributionDetailRead.model_validate(d) for d in details]
    return read
