from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/suppliers", tags=["供應商設定"])


@router.get("", response_model=list[schemas.SupplierRead])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).order_by(models.Supplier.supplier_id).all()


@router.post("", response_model=schemas.SupplierRead)
def create_supplier(payload: schemas.SupplierCreate, db: Session = Depends(get_db)):
    if db.get(models.Supplier, payload.supplier_id) is not None:
        raise HTTPException(400, "供應商編號已存在")
    row = models.Supplier(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{supplier_id}", response_model=schemas.SupplierRead)
def update_supplier(supplier_id: str, payload: schemas.SupplierUpdate, db: Session = Depends(get_db)):
    row = db.get(models.Supplier, supplier_id)
    if row is None:
        raise HTTPException(404, "供應商不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: str, db: Session = Depends(get_db)):
    row = db.get(models.Supplier, supplier_id)
    if row is None:
        raise HTTPException(404, "供應商不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}
