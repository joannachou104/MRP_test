from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/import-logs", tags=["資料匯入中心"])


@router.get("", response_model=list[schemas.ImportLogRead])
def list_import_logs(import_type: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.ImportLog)
    if import_type:
        query = query.filter(models.ImportLog.import_type == import_type)
    return query.order_by(models.ImportLog.imported_at.desc()).limit(limit).all()
