from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_procurement_permission, CurrentUser
from app.services import import_service, file_parser, changelog_service

router = APIRouter(prefix="/api/products", tags=["商品管理"])


@router.get("", response_model=list[schemas.ProductRead])
def list_products(
    status: Optional[str] = None,
    stock_nature: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ProductMaster)
    if status:
        query = query.filter(models.ProductMaster.status == status)
    if stock_nature:
        query = query.filter(models.ProductMaster.stock_nature == stock_nature)
    if category:
        query = query.filter(models.ProductMaster.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.ProductMaster.product_id.like(like)) | (models.ProductMaster.product_name.like(like))
        )
    return query.order_by(models.ProductMaster.product_id).all()


@router.get("/{product_id}", response_model=schemas.ProductRead)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.get(models.ProductMaster, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    return product


@router.post("", response_model=schemas.ProductRead)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if db.get(models.ProductMaster, payload.product_id) is not None:
        raise HTTPException(400, "商品編號已存在")
    product = models.ProductMaster(**payload.model_dump(), updated_by=user.name)
    db.add(product)
    changelog_service.log(db, "create", "product_master", payload.product_id, user.name)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductRead)
def update_product(
    product_id: str,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    product = db.get(models.ProductMaster, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    product.updated_by = user.name
    product.updated_at = datetime.utcnow()
    changelog_service.log(db, "update", "product_master", product_id, user.name)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/stock-planning", response_model=schemas.ProductRead)
def toggle_stock_planning(
    product_id: str,
    stock_planning: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    product = db.get(models.ProductMaster, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    if stock_planning not in ("active", "manual"):
        raise HTTPException(400, "stock_planning 需為 active 或 manual")
    product.stock_planning = stock_planning
    product.updated_by = user.name
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


@router.post("/import")
async def import_products_endpoint(
    mode: str = Form(...),  # 'create' | 'update'
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if mode not in ("create", "update"):
        raise HTTPException(400, "mode 需為 create 或 update")
    content = await file.read()
    rows = file_parser.parse_upload_to_rows(file, content)
    log = import_service.import_products(db, rows, mode, file.filename or "", user.name)
    return schemas.ImportLogRead.model_validate(log)
