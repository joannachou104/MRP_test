from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, CurrentUser
from app.services import file_parser, import_service

router = APIRouter(prefix="/api/processing-orders", tags=["加工配送管理"])


@router.get("", response_model=list[schemas.ProcessingOrderRead])
def list_processing_orders(
    product_id: str | None = None,
    plant_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ProcessingOrder)
    if product_id:
        query = query.filter(models.ProcessingOrder.product_id == product_id)
    if plant_id:
        query = query.filter(models.ProcessingOrder.plant_id == plant_id)
    return query.order_by(models.ProcessingOrder.required_date).all()


@router.post("/import")
async def import_processing_orders(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """委外加工排程完全來自 ERP 委外加工明細匯入,系統不自動產生排程建議。"""
    content = await file.read()
    rows = file_parser.parse_upload_to_rows(file, content)
    errors = []
    success_count = 0
    batch_id = import_service.new_batch_id("PO")

    for idx, row in enumerate(rows, start=1):
        product_id = str(row.get("product_id", "")).strip()
        plant_id = str(row.get("plant_id", "")).strip()
        try:
            planned_qty = float(row.get("planned_qty") or 0)
            required_date = row["required_date"]
            if isinstance(required_date, str):
                from datetime import datetime as dt

                required_date = dt.strptime(required_date[:10], "%Y-%m-%d").date()
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "error": f"欄位格式錯誤: {exc}"})
            continue

        if db.get(models.ProductMaster, product_id) is None:
            errors.append({"row": idx, "error": f"商品 {product_id} 不存在"})
            continue
        if db.get(models.ProcessingPlant, plant_id) is None:
            errors.append({"row": idx, "error": f"加工廠 {plant_id} 不存在"})
            continue

        db.add(
            models.ProcessingOrder(
                product_id=product_id,
                plant_id=plant_id,
                planned_qty=planned_qty,
                required_date=required_date,
                import_batch_id=batch_id,
            )
        )
        success_count += 1

    import_service.create_import_log(
        db, batch_id, "processing_order", file.filename or "", user.name, success_count, errors
    )
    db.commit()
    return {"batch_id": batch_id, "success_count": success_count, "error_count": len(errors), "errors": errors}
