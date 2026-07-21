"""跨節點需求展開:combo/成品的通路預測(獨立需求)沿 BOM 逐層往下累加為
半成品/原料的相依需求,再加總為每個節點的 gross 月需求。

採拓樸排序(Kahn's algorithm):父項(BOM parent,即較上層/較終端的商品)
必須先被計算出總需求,才能把該需求 x quantity_per_unit 累加給子項(較底層原料)。
"""
from collections import defaultdict, deque
from sqlalchemy.orm import Session

from app import models
from app.services import forecast_service


def compute_gross_monthly_demand(db: Session, year_month: str) -> dict[str, float]:
    normal_products = (
        db.query(models.ProductMaster).filter(models.ProductMaster.stock_nature == "normal").all()
    )
    normal_ids = {p.product_id for p in normal_products}

    gross_demand: dict[str, float] = {}
    for pid in normal_ids:
        gross_demand[pid] = forecast_service.get_product_total_monthly_forecast(db, pid, year_month)

    bom_rows = (
        db.query(models.Bom)
        .filter(models.Bom.parent_product_id.in_(normal_ids), models.Bom.child_product_id.in_(normal_ids))
        .all()
    )

    child_of_parent: dict[str, list[tuple[str, float]]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    for row in bom_rows:
        child_of_parent[row.parent_product_id].append((row.child_product_id, float(row.quantity_per_unit)))
        in_degree[row.child_product_id] += 1

    queue: deque[str] = deque(pid for pid in normal_ids if in_degree.get(pid, 0) == 0)
    processed: set[str] = set()

    while queue:
        parent_id = queue.popleft()
        if parent_id in processed:
            continue
        processed.add(parent_id)
        for child_id, qty_per_unit in child_of_parent.get(parent_id, []):
            gross_demand[child_id] = gross_demand.get(child_id, 0) + gross_demand[parent_id] * qty_per_unit
            in_degree[child_id] -= 1
            if in_degree[child_id] <= 0:
                queue.append(child_id)

    # 若資料存在循環引用,剩餘未處理節點仍保留目前累積值,不中斷運算
    return gross_demand
