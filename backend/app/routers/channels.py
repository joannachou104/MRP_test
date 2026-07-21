from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, CurrentUser
from app.services import import_service, file_parser, forecast_service

router = APIRouter(prefix="/api/channels", tags=["通路管理"])


@router.get("", response_model=list[schemas.ChannelRead])
def list_channels(db: Session = Depends(get_db)):
    return db.query(models.SalesChannel).order_by(models.SalesChannel.channel_id).all()


@router.post("", response_model=schemas.ChannelRead)
def create_channel(payload: schemas.ChannelCreate, db: Session = Depends(get_db)):
    if db.get(models.SalesChannel, payload.channel_id) is not None:
        raise HTTPException(400, "通路編號已存在")
    row = models.SalesChannel(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/forecasts", response_model=list[schemas.ChannelForecastRead])
def list_forecasts(
    channel_id: str | None = None,
    product_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ChannelForecastExternal)
    if channel_id:
        query = query.filter(models.ChannelForecastExternal.channel_id == channel_id)
    if product_id:
        query = query.filter(models.ChannelForecastExternal.product_id == product_id)
    return query.order_by(models.ChannelForecastExternal.period_value.desc()).all()


@router.post("/forecasts/import")
async def import_forecast_endpoint(
    mode: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if mode not in ("create", "update"):
        raise HTTPException(400, "mode 需為 create 或 update")
    content = await file.read()
    rows = file_parser.parse_upload_to_rows(file, content)
    log = import_service.import_channel_forecast(db, rows, mode, file.filename or "", user.name)
    return schemas.ImportLogRead.model_validate(log)


@router.get("/b2c-calc/{product_id}")
def get_b2c_calc(product_id: str, year_month: str, db: Session = Depends(get_db)):
    """B2C 通路計算結果查詢:近3個月銷量平均 x (1+YOY成長率),供查核用。"""
    channels = db.query(models.SalesChannel).filter(models.SalesChannel.forecast_source == "internal_calculated").all()
    result = []
    for ch in channels:
        forecast = forecast_service.get_b2c_monthly_forecast(db, product_id, ch.channel_id, year_month)
        result.append({"channel_id": ch.channel_id, "channel_name": ch.channel_name, "b2c_forecast_qty": forecast})
    return result
