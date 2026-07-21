"""缺口追溯:選定一個缺貨商品,沿 BOM 逐層往下,列出各節點最新一筆 mrp_result。"""
from sqlalchemy.orm import Session

from app import models
from app.services import bom_service


def get_latest_result(db: Session, product_id: str) -> models.MrpResult | None:
    return (
        db.query(models.MrpResult)
        .filter(models.MrpResult.product_id == product_id)
        .order_by(models.MrpResult.run_date.desc(), models.MrpResult.result_id.desc())
        .first()
    )


def trace_gap(db: Session, root_product_id: str) -> dict | None:
    tree = bom_service.expand_bom_tree(db, root_product_id)
    if tree is None:
        return None

    def build(node: bom_service.BomNode) -> dict:
        product = db.get(models.ProductMaster, node.product_id)
        result = get_latest_result(db, node.product_id)
        return {
            "product_id": node.product_id,
            "product_name": product.product_name if product else node.product_id,
            "level": node.level,
            "quantity_per_unit_from_parent": node.quantity_per_unit_from_parent,
            "total_multiplier": node.total_multiplier,
            "lead_time_days": product.lead_time_days if product else None,
            "lead_time_type": product.lead_time_type if product else None,
            "mrp_result": {
                "run_date": result.run_date.isoformat() if result else None,
                "forecast_demand": float(result.forecast_demand) if result else None,
                "current_stock": float(result.current_stock) if result else None,
                "sellable_days": float(result.sellable_days) if result else None,
                "net_requirement": float(result.net_requirement) if result else None,
                "suggested_order_qty": float(result.suggested_order_qty) if result else None,
                "suggested_order_deadline": result.suggested_order_deadline.isoformat()
                if result and result.suggested_order_deadline
                else None,
                "trigger_reason": result.trigger_reason if result else None,
            }
            if result
            else None,
            "children": [build(c) for c in node.children],
        }

    return build(tree)
