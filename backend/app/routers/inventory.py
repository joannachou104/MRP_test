from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, CurrentUser
from app.services import import_service, file_parser

router = APIRouter(prefix="/api/inventory", tags=["資料匯入中心"])


@router.get("", response_model=list[schemas.InventoryDailyRead])
def list_inventory(
    product_id: str | None = None,
    snapshot_date: date | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    query = db.query(models.InventoryDaily)
    if product_id:
        query = query.filter(models.InventoryDaily.product_id == product_id)
    if snapshot_date:
        query = query.filter(models.InventoryDaily.snapshot_date == snapshot_date)
    return query.order_by(models.InventoryDaily.snapshot_date.desc()).limit(limit).all()


@router.post("/import")
async def import_inventory_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """每日庫存上傳:單一入口,無新增/更新雙介面。snapshot_date 完全由系統依台灣時區自動帶入。"""
    content = await file.read()
    rows = file_parser.parse_upload_to_rows(file, content)
    result = import_service.import_inventory_daily(db, rows, file.filename or "", user.name)
    return {
        "log": schemas.ImportLogRead.model_validate(result["log"]),
        "snapshot_date": result["snapshot_date"],
        "is_first_upload_of_day": result["is_first_upload_of_day"],
        "message": result["message"],
    }
