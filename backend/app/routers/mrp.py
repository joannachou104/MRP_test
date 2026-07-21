from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import mrp_engine, gap_trace_service

router = APIRouter(prefix="/api/mrp", tags=["MRP 運算儀表板"])


@router.post("/run", response_model=list[schemas.MrpResultRead])
def run_mrp(run_date: date | None = None, db: Session = Depends(get_db)):
    results = mrp_engine.run_mrp(db, run_date)
    return results


@router.get("/results", response_model=list[schemas.MrpResultRead])
def list_results(
    run_date: date | None = None,
    category: str | None = None,
    trigger_only: bool = False,
    review_status: str | None = None,
    recommendation_type: str | None = None,
    db: Session = Depends(get_db),
):
    if run_date is None:
        latest = db.query(models.MrpResult.run_date).order_by(models.MrpResult.run_date.desc()).first()
        run_date = latest[0] if latest else None
    query = db.query(models.MrpResult).filter(models.MrpResult.run_date == run_date)
    if trigger_only:
        query = query.filter(models.MrpResult.net_requirement > 0)
    if review_status:
        query = query.filter(models.MrpResult.review_status == review_status)
    if recommendation_type:
        query = query.filter(models.MrpResult.recommendation_type == recommendation_type)
    results = query.all()
    if category:
        product_ids = {
            p.product_id
            for p in db.query(models.ProductMaster).filter(models.ProductMaster.category == category).all()
        }
        results = [r for r in results if r.product_id in product_ids]
    return results


@router.get("/latest-run-date")
def get_latest_run_date(db: Session = Depends(get_db)):
    latest = db.query(models.MrpResult.run_date).order_by(models.MrpResult.run_date.desc()).first()
    return {"run_date": latest[0].isoformat() if latest else None}


@router.get("/gap-trace/{product_id}")
def gap_trace(product_id: str, db: Session = Depends(get_db)):
    tree = gap_trace_service.trace_gap(db, product_id)
    if tree is None:
        raise HTTPException(404, "商品不存在")
    return tree


@router.get("/arrival-reminders")
def arrival_reminders(as_of: date | None = None, db: Session = Depends(get_db)):
    return mrp_engine.get_arrival_reminders(db, as_of or date.today())
