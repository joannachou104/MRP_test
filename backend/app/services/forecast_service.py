"""三通路需求預測邏輯:
- 大宗採購(external_quarterly):季預測按 50/30/20 拆分至三個月
- 飯店採購(external_monthly):月預測直接採用
- B2C(internal_calculated):近3個月銷量平均 x (1 + 去年同期YOY成長率),YOY 上限 ±50%
"""
import calendar
from datetime import date
from sqlalchemy.orm import Session

from app import models

BULK_QUARTER_SPLIT_RATIOS = [0.5, 0.3, 0.2]  # 該季第1/2/3個月比例
YOY_CAP = 0.5


def year_month_to_quarter(year_month: str) -> tuple[str, int]:
    """'2026-07' -> ('2026-Q3', 1)  回傳所屬季別與該月在季內的位置(1~3,0-index+1)"""
    year, month = year_month.split("-")
    month = int(month)
    quarter_num = (month - 1) // 3 + 1
    position_in_quarter = (month - 1) % 3  # 0,1,2
    return f"{year}-Q{quarter_num}", position_in_quarter


def shift_year_month(year_month: str, months_delta: int) -> str:
    year, month = (int(x) for x in year_month.split("-"))
    total = year * 12 + (month - 1) + months_delta
    new_year, new_month = divmod(total, 12)
    return f"{new_year}-{new_month + 1:02d}"


def days_in_month(year_month: str) -> int:
    year, month = (int(x) for x in year_month.split("-"))
    return calendar.monthrange(year, month)[1]


def get_bulk_monthly_forecast(db: Session, product_id: str, channel_id: str, year_month: str) -> float:
    quarter_value, position = year_month_to_quarter(year_month)
    row = (
        db.query(models.ChannelForecastExternal)
        .filter(
            models.ChannelForecastExternal.channel_id == channel_id,
            models.ChannelForecastExternal.product_id == product_id,
            models.ChannelForecastExternal.period_type == "quarter",
            models.ChannelForecastExternal.period_value == quarter_value,
        )
        .first()
    )
    if row is None:
        return 0.0
    return float(row.forecast_qty) * BULK_QUARTER_SPLIT_RATIOS[position]


def get_hotel_monthly_forecast(db: Session, product_id: str, channel_id: str, year_month: str) -> float:
    row = (
        db.query(models.ChannelForecastExternal)
        .filter(
            models.ChannelForecastExternal.channel_id == channel_id,
            models.ChannelForecastExternal.product_id == product_id,
            models.ChannelForecastExternal.period_type == "month",
            models.ChannelForecastExternal.period_value == year_month,
        )
        .first()
    )
    if row is None:
        return 0.0
    return float(row.forecast_qty)


def _monthly_net_qty(db: Session, product_id: str, channel_id: str, year_month: str) -> float:
    """該月銷貨扣除銷退的淨數量。"""
    year, month = (int(x) for x in year_month.split("-"))
    start = date(year, month, 1)
    end_day = days_in_month(year_month)
    end = date(year, month, end_day)

    rows = (
        db.query(models.SalesTransaction)
        .filter(
            models.SalesTransaction.product_id == product_id,
            models.SalesTransaction.channel_id == channel_id,
            models.SalesTransaction.doc_date >= start,
            models.SalesTransaction.doc_date <= end,
        )
        .all()
    )
    total = 0.0
    for r in rows:
        qty = float(r.quantity)
        total += qty if r.doc_type == "sale" else -qty
    return total


def get_b2c_monthly_forecast(db: Session, product_id: str, channel_id: str, as_of_year_month: str) -> float:
    """B2C 預測 = 近3個月銷量平均 x (1 + 去年同期YOY成長率),YOY 上限 ±50%。
    「近3個月」定義為 as_of_year_month 往前推的3個完整月份(不含當月)。
    「去年同期」為同一組3個月往前推一年。
    """
    recent_months = [shift_year_month(as_of_year_month, -delta) for delta in (1, 2, 3)]
    last_year_months = [shift_year_month(m, -12) for m in recent_months]

    recent_avg = sum(_monthly_net_qty(db, product_id, channel_id, m) for m in recent_months) / 3
    last_year_avg = sum(_monthly_net_qty(db, product_id, channel_id, m) for m in last_year_months) / 3

    if last_year_avg == 0:
        return max(recent_avg, 0)

    yoy = (recent_avg - last_year_avg) / last_year_avg
    yoy = max(-YOY_CAP, min(YOY_CAP, yoy))
    forecast = recent_avg * (1 + yoy)
    return max(forecast, 0)


def get_product_total_monthly_forecast(db: Session, product_id: str, year_month: str) -> float:
    """單一商品的 forecast_demand = 三通路預測加總(依各通路 forecast_source 分流計算)。"""
    total = 0.0
    channels = db.query(models.SalesChannel).all()
    for ch in channels:
        if ch.forecast_source == "external_quarterly":
            total += get_bulk_monthly_forecast(db, product_id, ch.channel_id, year_month)
        elif ch.forecast_source == "external_monthly":
            total += get_hotel_monthly_forecast(db, product_id, ch.channel_id, year_month)
        elif ch.forecast_source == "internal_calculated":
            total += get_b2c_monthly_forecast(db, product_id, ch.channel_id, year_month)
    return total


def get_avg_daily_demand(db: Session, product_id: str, as_of: date) -> float:
    year_month = f"{as_of.year}-{as_of.month:02d}"
    monthly_total = get_product_total_monthly_forecast(db, product_id, year_month)
    return monthly_total / days_in_month(year_month)
