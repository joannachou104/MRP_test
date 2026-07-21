from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, CurrentUser
from app.services import import_service, file_parser

router = APIRouter(prefix="/api/sales", tags=["資料匯入中心"])


@router.get("", response_model=list[schemas.SalesTransactionRead])
def list_sales(
    product_id: str | None = None,
    channel_id: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(models.SalesTransaction)
    if product_id:
        query = query.filter(models.SalesTransaction.product_id == product_id)
    if channel_id:
        query = query.filter(models.SalesTransaction.channel_id == channel_id)
    return query.order_by(models.SalesTransaction.doc_date.desc()).limit(limit).all()


@router.post("/import")
async def import_sales_endpoint(
    upload_type: str = Form(...),  # 'bulk_initial' | 'daily_incremental'
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if upload_type not in ("bulk_initial", "daily_incremental"):
        raise HTTPException(400, "upload_type 需為 bulk_initial 或 daily_incremental")
    content = await file.read()
    rows = file_parser.parse_upload_to_rows(file, content)
    log = import_service.import_sales_transactions(
        db, rows, upload_type == "bulk_initial", file.filename or "", user.name
    )
    return schemas.ImportLogRead.model_validate(log)
