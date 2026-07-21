"""BOM 展開邏輯:多層遞迴展開,僅 stock_nature='normal' 的商品參與。"""
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app import models


@dataclass
class BomNode:
    product_id: str
    quantity_per_unit_from_parent: float  # 相對於直接父項的每單位用量
    total_multiplier: float  # 展開到根節點的累積倍率(root=1)
    level: int
    parent_product_id: str | None
    children: list["BomNode"] = field(default_factory=list)


def get_children(db: Session, parent_product_id: str) -> list[models.Bom]:
    return (
        db.query(models.Bom)
        .filter(models.Bom.parent_product_id == parent_product_id)
        .all()
    )


def expand_bom_tree(
    db: Session,
    root_product_id: str,
    _visited: set[str] | None = None,
) -> BomNode | None:
    """遞迴展開某商品完整 BOM 樹。跳過 stock_nature != 'normal' 的節點(視為葉節點不再往下展開)。"""
    if _visited is None:
        _visited = set()

    product = db.get(models.ProductMaster, root_product_id)
    if product is None:
        return None

    root = BomNode(
        product_id=root_product_id,
        quantity_per_unit_from_parent=1,
        total_multiplier=1,
        level=0,
        parent_product_id=None,
    )
    _build_children(db, root, _visited | {root_product_id})
    return root


def _build_children(db: Session, node: BomNode, visited: set[str]) -> None:
    product = db.get(models.ProductMaster, node.product_id)
    if product is None or product.stock_nature != "normal":
        return  # non_stock 商品跳過 BOM 展開

    bom_rows = get_children(db, node.product_id)
    for row in bom_rows:
        if row.child_product_id in visited:
            continue  # 避免循環引用造成無限遞迴
        child_product = db.get(models.ProductMaster, row.child_product_id)
        if child_product is None or child_product.stock_nature != "normal":
            continue
        child_node = BomNode(
            product_id=row.child_product_id,
            quantity_per_unit_from_parent=float(row.quantity_per_unit),
            total_multiplier=node.total_multiplier * float(row.quantity_per_unit),
            level=node.level + 1,
            parent_product_id=node.product_id,
        )
        node.children.append(child_node)
        _build_children(db, child_node, visited | {row.child_product_id})


def flatten_tree(node: BomNode) -> list[BomNode]:
    result = [node]
    for child in node.children:
        result.extend(flatten_tree(child))
    return result


def get_parents(db: Session, child_product_id: str) -> list[models.Bom]:
    """反查:找出所有以此節點為 child_product_id 的上層節點(用於配送清單運算)。"""
    return (
        db.query(models.Bom)
        .filter(models.Bom.child_product_id == child_product_id)
        .all()
    )
