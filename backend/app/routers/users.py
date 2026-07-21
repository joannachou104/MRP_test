from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/users", tags=["系統設定/權限"])


@router.get("", response_model=list[schemas.AppUserRead])
def list_users(db: Session = Depends(get_db)):
    """本機測試用簡易使用者清單(非正式帳密系統),供前端角色切換選單使用。"""
    return db.query(models.AppUser).all()


@router.get("/change-log", response_model=list[schemas.ChangeLogRead])
def list_change_log(limit: int = 200, db: Session = Depends(get_db)):
    return db.query(models.ChangeLog).order_by(models.ChangeLog.operated_at.desc()).limit(limit).all()
