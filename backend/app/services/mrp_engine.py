"""MRP 運算核心:
- 淨需求/建議採購量公式(3.3)
- 前置時間反推(3.4,經由 demand_explosion 的逐節點展開自然達成,見下方說明)
- 主動/人工參考分流(3.5)
- 在途到貨提醒(3.6)
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app import models
from app.services import forecast_service, demand_explosion

BUFFER_DAYS = 14


def get_latest_stock(db: Session, product_id: str, as_of: date) -> float:
    row = (
        db.query(models.InventoryDaily)
        .filter(models.InventoryDaily.product_id == product_id, models.InventoryDaily.snapshot_date <= as_of)
        .order_by(models.InventoryDaily.snapshot_date.desc())
        .first()
    )
    return float(row.quantity) if row else 0.0


def get_pending_qty(db: Session, product_id: str) -> float:
    rows = (
        db.query(models.ProcurementPending)
        .filter(models.ProcurementPending.product_id == product_id, models.ProcurementPending.status == "pending")
        .all()
    )
    return sum(float(r.expected_qty) for r in rows)


def run_mrp(db: Session, run_date: date | None = None) -> list[models.MrpResult]:
    if run_date is None:
        run_date = date.today()
    year_month = f"{run_date.year}-{run_date.month:02d}"

    gross_demand = demand_explosion.compute_gross_monthly_demand(db, year_month)
    days = forecast_service.days_in_month(year_month)

    # 同一 run_date 重新運算時先清除舊結果,允許本機測試重複執行
    db.query(models.MrpResult).filter(models.MrpResult.run_date == run_date).delete()

    normal_products = (
        db.query(models.ProductMaster)
        .filter(models.ProductMaster.stock_nature == "normal", models.ProductMaster.status == "active")
        .all()
    )

    results: list[models.MrpResult] = []
    for product in normal_products:
        monthly_demand = gross_demand.get(product.product_id, 0.0)
        avg_daily_demand = monthly_demand / days if days else 0.0
        current_stock = get_latest_stock(db, product.product_id, run_date)
        pending_qty = get_pending_qty(db, product.product_id)
        safety_stock = float(product.safety_stock_qty or 0)
        lead_time = int(product.lead_time_days or 0)

        sellable_days = (current_stock / avg_daily_demand) if avg_daily_demand > 0 else None

        trigger_a = sellable_days is not None and (sellable_days - BUFFER_DAYS) < lead_time
        trigger_b = current_stock < safety_stock

        if trigger_a and trigger_b:
            trigger_reason = "both"
        elif trigger_a:
            trigger_reason = "lead_time_breach"
        elif trigger_b:
            trigger_reason = "below_safety_stock"
        else:
            trigger_reason = None

        coverage_days = lead_time + BUFFER_DAYS
        period_demand = avg_daily_demand * coverage_days
        net_requirement = max(period_demand - current_stock - pending_qty, 0)
        suggested_order_qty = net_requirement + safety_stock if net_requirement > 0 else 0.0

        # 建議下單期限:此節點自身的需求日(現有庫存耗盡日)往前扣除自身前置時間。
        # 因每個 BOM 節點各自有獨立的 mrp_result 記錄,且下層節點的 gross_demand
        # 已經是上層需求逐層展開後的相依需求,故「逐層反推」已透過每個節點各自
        # 套用自己的 lead_time_days 自然達成,不需在單一欄位內重複串接整條鏈。
        if sellable_days is not None:
            need_date = run_date + timedelta(days=int(sellable_days))
            suggested_order_deadline = need_date - timedelta(days=lead_time)
        else:
            suggested_order_deadline = None

        recommendation_type = "active" if product.stock_planning == "active" else "reference"

        ignore_row = (
            db.query(models.MrpIgnore).filter(models.MrpIgnore.product_id == product.product_id).first()
        )
        if ignore_row is not None:
            if net_requirement <= 0:
                # 缺口已消失,自動解除忽略設定
                db.delete(ignore_row)
                review_status = "unreviewed"
            else:
                review_status = "ignored"
        else:
            review_status = "unreviewed"

        result = models.MrpResult(
            run_date=run_date,
            product_id=product.product_id,
            forecast_demand=monthly_demand,
            current_stock=current_stock,
            sellable_days=sellable_days if sellable_days is not None else 0,
            net_requirement=net_requirement,
            suggested_order_qty=suggested_order_qty,
            suggested_order_deadline=suggested_order_deadline,
            trigger_reason=trigger_reason,
            recommendation_type=recommendation_type,
            review_status=review_status,
        )
        db.add(result)
        results.append(result)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


def get_arrival_reminders(db: Session, as_of: date) -> list[dict]:
    """3.6 在途到貨提醒:今日庫存增量 >= 該商品所有在途量加總 -> 疑似已到貨。"""
    yesterday = as_of - timedelta(days=1)
    reminders = []

    pending_products = (
        db.query(models.ProcurementPending.product_id)
        .filter(models.ProcurementPending.status == "pending")
        .distinct()
        .all()
    )
    for (product_id,) in pending_products:
        today_stock = get_latest_stock(db, product_id, as_of)
        yesterday_stock = get_latest_stock(db, product_id, yesterday)
        increase = today_stock - yesterday_stock
        pending_qty = get_pending_qty(db, product_id)
        if pending_qty > 0 and increase >= pending_qty:
            reminders.append(
                {
                    "product_id": product_id,
                    "stock_increase": increase,
                    "pending_qty": pending_qty,
                    "message": "疑似已到貨,請確認",
                }
            )
    return reminders
