from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/plants", tags=["加工配送管理"])


@router.get("", response_model=list[schemas.PlantRead])
def list_plants(db: Session = Depends(get_db)):
    return db.query(models.ProcessingPlant).order_by(models.ProcessingPlant.plant_id).all()


@router.post("", response_model=schemas.PlantRead)
def create_plant(payload: schemas.PlantCreate, db: Session = Depends(get_db)):
    if db.get(models.ProcessingPlant, payload.plant_id) is not None:
        raise HTTPException(400, "加工廠編號已存在")
    row = models.ProcessingPlant(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{plant_id}", response_model=schemas.PlantRead)
def update_plant(plant_id: str, payload: schemas.PlantUpdate, db: Session = Depends(get_db)):
    row = db.get(models.ProcessingPlant, plant_id)
    if row is None:
        raise HTTPException(404, "加工廠不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
