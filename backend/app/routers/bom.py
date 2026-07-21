from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, CurrentUser
from app.services import import_service, file_parser, bom_service

router = APIRouter(prefix="/api/bom", tags=["BOM 管理"])


@router.get("", response_model=list[schemas.BomRead])
def list_bom(parent_product_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Bom)
    if parent_product_id:
        query = query.filter(models.Bom.parent_product_id == parent_product_id)
    return query.order_by(models.Bom.parent_product_id).all()


@router.get("/tree/{root_product_id}")
def get_bom_tree(root_product_id: str, db: Session = Depends(get_db)):
    tree = bom_service.expand_bom_tree(db, root_product_id)
    if tree is None:
        raise HTTPException(404, "商品不存在")

    def serialize(node: bom_service.BomNode) -> dict:
        product = db.get(models.ProductMaster, node.product_id)
        return {
            "product_id": node.product_id,
            "product_name": product.product_name if product else node.product_id,
            "quantity_per_unit_from_parent": node.quantity_per_unit_from_parent,
            "total_multiplier": node.total_multiplier,
            "level": node.level,
            "lead_time_days": product.lead_time_days if product else None,
            "lead_time_type": product.lead_time_type if product else None,
            "children": [serialize(c) for c in node.children],
        }

    return serialize(tree)


@router.post("", response_model=schemas.BomRead)
def create_bom_row(payload: schemas.BomCreate, db: Session = Depends(get_db)):
    if db.get(models.ProductMaster, payload.parent_product_id) is None or db.get(
        models.ProductMaster, payload.child_product_id
    ) is None:
        raise HTTPException(400, "parent/child 商品編號不存在")
    existing = (
        db.query(models.Bom)
        .filter(
            models.Bom.parent_product_id == payload.parent_product_id,
            models.Bom.child_product_id == payload.child_product_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(400, "此 BOM 關係已存在")
    row = models.Bom(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{bom_id}")
def delete_bom_row(bom_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Bom, bom_id)
    if row is None:
        raise HTTPException(404, "BOM 資料不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/import")
async def import_bom_endpoint(
    mode: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if mode not in ("create", "update"):
        raise HTTPException(400, "mode 需為 create 或 update")
    content = await file.read()
    rows = file_parser.parse_upload_to_rows(file, content)
    log = import_service.import_bom(db, rows, mode, file.filename or "", user.name)
    return schemas.ImportLogRead.model_validate(log)
