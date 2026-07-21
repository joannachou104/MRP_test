"""本機測試示範資料:一組多層 BOM(原料 -> 半成品 -> 成品 -> 組合品)、
供應商/加工廠/通路/預測/銷貨歷史/庫存快照/委外排程,執行後即可直接在
MRP 儀表板看到有意義的缺口與建議。

用法: python -m app.seed
"""
import random
from datetime import date, timedelta

from app.database import Base, engine, SessionLocal
from app import models


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed(db)
        db.commit()
        print("Seed 完成。")
    finally:
        db.close()


def _seed(db):
    # --- 使用者(角色切換模擬) ---------------------------------------------
    db.add_all(
        [
            models.AppUser(user_id="admin", display_name="系統管理員", role="admin"),
            models.AppUser(user_id="buyer", display_name="採購人員 Amy", role="procurement"),
            models.AppUser(user_id="viewer", display_name="唯讀訪客", role="viewer"),
        ]
    )

    # --- 供應商 --------------------------------------------------------------
    db.add_all(
        [
            models.Supplier(supplier_id="SUP-BOTTLE", supplier_name="優美塑膠瓶罐廠", min_order_qty=2000),
            models.Supplier(supplier_id="SUP-OIL", supplier_name="天然精油原料商", min_order_qty=50),
            models.Supplier(supplier_id="SUP-BOX", supplier_name="精緻紙盒印刷廠", min_order_qty=500),
            models.Supplier(supplier_id="SUP-PUMP", supplier_name="精密壓頭零件廠", min_order_qty=1000),
        ]
    )

    # --- 加工廠/包裝廠 --------------------------------------------------------
    db.add_all(
        [
            models.ProcessingPlant(plant_id="PLANT-FILL", plant_name="日興充填加工廠", contact_info="03-1234567"),
            models.ProcessingPlant(plant_id="PLANT-FILL2", plant_name="盛揚充填加工廠", contact_info="04-2345678"),
            models.ProcessingPlant(plant_id="PLANT-PACK", plant_name="美聯禮盒包裝廠", contact_info="02-3456789"),
        ]
    )

    # --- 通路 -----------------------------------------------------------------
    db.add_all(
        [
            models.SalesChannel(channel_id="BULK", channel_name="大宗採購", forecast_source="external_quarterly"),
            models.SalesChannel(channel_id="HOTEL", channel_name="飯店採購", forecast_source="external_monthly"),
            models.SalesChannel(channel_id="B2C", channel_name="B2C 官網", forecast_source="internal_calculated"),
        ]
    )
    db.flush()

    # --- 商品主檔 ---------------------------------------------------------
    # 原料
    products = [
        dict(product_id="RAW-BOTTLE-500", product_name="500ml 塑膠空瓶", unit="個", category="包材",
             is_composite=False, lead_time_days=15, lead_time_type="procurement", safety_stock_qty=1000,
             supplier_id="SUP-BOTTLE"),
        dict(product_id="RAW-PUMP", product_name="按壓頭", unit="個", category="包材",
             is_composite=False, lead_time_days=12, lead_time_type="procurement", safety_stock_qty=1000,
             supplier_id="SUP-PUMP"),
        dict(product_id="RAW-OIL-SH", product_name="洗髮精香精原料", unit="kg", category="原料",
             is_composite=False, lead_time_days=20, lead_time_type="procurement", safety_stock_qty=80,
             supplier_id="SUP-OIL"),
        dict(product_id="RAW-OIL-SG", product_name="沐浴乳香精原料", unit="kg", category="原料",
             is_composite=False, lead_time_days=20, lead_time_type="procurement", safety_stock_qty=80,
             supplier_id="SUP-OIL"),
        dict(product_id="RAW-BOX-GIFT", product_name="禮盒外盒", unit="個", category="包材",
             is_composite=False, lead_time_days=18, lead_time_type="procurement", safety_stock_qty=300,
             supplier_id="SUP-BOX"),
        # 半成品(調製完成、待充填的原液,需經加工廠調製)
        dict(product_id="SEMI-SH-BULK", product_name="洗髮精原液(調製)", unit="kg", category="半成品",
             is_composite=True, lead_time_days=7, lead_time_type="processing", safety_stock_qty=100,
             processing_plant_id="PLANT-FILL"),
        dict(product_id="SEMI-SG-BULK", product_name="沐浴乳原液(調製)", unit="kg", category="半成品",
             is_composite=True, lead_time_days=7, lead_time_type="processing", safety_stock_qty=100,
             processing_plant_id="PLANT-FILL2"),
        # 成品(充填+QC放行,兩段前置時間分別由 processing 與 qc 節點表示)
        dict(product_id="FG-SHAMPOO-500", product_name="洗髮精 500ml", unit="瓶", category="成品",
             is_composite=True, lead_time_days=4, lead_time_type="qc", safety_stock_qty=300,
             processing_plant_id="PLANT-FILL"),
        dict(product_id="FG-SHOWERGEL-500", product_name="沐浴乳 500ml", unit="瓶", category="成品",
             is_composite=True, lead_time_days=4, lead_time_type="qc", safety_stock_qty=300,
             processing_plant_id="PLANT-FILL2"),
        # 組合品(禮盒,由包裝廠組裝)
        dict(product_id="COMBO-GIFTSET", product_name="洗沐禮盒組", unit="組", category="組合品",
             is_composite=True, lead_time_days=3, lead_time_type="processing", safety_stock_qty=50,
             processing_plant_id="PLANT-PACK"),
        # 非庫存項目示範(贈品,完全跳過 BOM/MRP)
        dict(product_id="GIFT-SAMPLE", product_name="試用包贈品", unit="個", category="贈品",
             is_composite=False, stock_nature="non_stock", lead_time_days=0, lead_time_type="procurement",
             safety_stock_qty=0),
        # 人工判斷類示範(一次性業務需求)
        dict(product_id="FG-TRAVEL-SET", product_name="旅行組(一次性商用)", unit="組", category="成品",
             is_composite=False, stock_planning="manual", lead_time_days=10, lead_time_type="procurement",
             safety_stock_qty=20),
    ]
    for p in products:
        db.add(models.ProductMaster(updated_by="seed", **p))
    db.flush()

    # --- BOM --------------------------------------------------------------
    bom_rows = [
        ("SEMI-SH-BULK", "RAW-OIL-SH", 1.0),
        ("SEMI-SG-BULK", "RAW-OIL-SG", 1.0),
        ("FG-SHAMPOO-500", "SEMI-SH-BULK", 0.5),   # 每瓶 500ml 用 0.5kg 原液
        ("FG-SHAMPOO-500", "RAW-BOTTLE-500", 1.0),
        ("FG-SHAMPOO-500", "RAW-PUMP", 1.0),
        ("FG-SHOWERGEL-500", "SEMI-SG-BULK", 0.5),
        ("FG-SHOWERGEL-500", "RAW-BOTTLE-500", 1.0),
        ("FG-SHOWERGEL-500", "RAW-PUMP", 1.0),
        ("COMBO-GIFTSET", "FG-SHAMPOO-500", 1.0),
        ("COMBO-GIFTSET", "FG-SHOWERGEL-500", 1.0),
        ("COMBO-GIFTSET", "RAW-BOX-GIFT", 1.0),
    ]
    for parent, child, qty in bom_rows:
        db.add(models.Bom(parent_product_id=parent, child_product_id=child, quantity_per_unit=qty))

    # --- 通路預測 ---------------------------------------------------------
    # 大宗:提供本季與下一季預測(季預測會由系統拆分 50/30/20)
    for q in ("2026-Q3", "2026-Q4"):
        db.add(
            models.ChannelForecastExternal(
                channel_id="BULK", product_id="FG-SHAMPOO-500", period_type="quarter",
                period_value=q, forecast_qty=1200,
            )
        )
        db.add(
            models.ChannelForecastExternal(
                channel_id="BULK", product_id="COMBO-GIFTSET", period_type="quarter",
                period_value=q, forecast_qty=300,
            )
        )
    # 飯店:直接給月預測
    for m in ("2026-07", "2026-08", "2026-09"):
        db.add(
            models.ChannelForecastExternal(
                channel_id="HOTEL", product_id="FG-SHOWERGEL-500", period_type="month",
                period_value=m, forecast_qty=400,
            )
        )
        db.add(
            models.ChannelForecastExternal(
                channel_id="HOTEL", product_id="COMBO-GIFTSET", period_type="month",
                period_value=m, forecast_qty=150,
            )
        )

    # --- 銷貨歷史(供 B2C 近3個月平均 + 去年同期 YOY 使用) ---------------------
    random.seed(42)
    today = date.today()
    b2c_products = ["FG-SHAMPOO-500", "FG-SHOWERGEL-500", "COMBO-GIFTSET"]
    base_qty = {"FG-SHAMPOO-500": 260, "FG-SHOWERGEL-500": 220, "COMBO-GIFTSET": 90}

    for months_ago in range(1, 16):  # 涵蓋近3個月與去年同期(15個月前)
        year = today.year
        month = today.month - months_ago
        while month <= 0:
            month += 12
            year -= 1
        doc_date = date(year, month, 15)
        for pid in b2c_products:
            growth_factor = 1.15 if months_ago <= 3 else 1.0  # 今年比去年成長約15%
            qty = round(base_qty[pid] * growth_factor * random.uniform(0.9, 1.1))
            db.add(
                models.SalesTransaction(
                    doc_no=f"SO-{year}{month:02d}-{pid}",
                    doc_date=doc_date,
                    product_id=pid,
                    channel_id="B2C",
                    quantity=qty,
                    doc_type="sale",
                )
            )
            if months_ago == 2:  # 示範一筆銷退
                db.add(
                    models.SalesTransaction(
                        doc_no=f"RT-{year}{month:02d}-{pid}",
                        doc_date=doc_date + timedelta(days=3),
                        product_id=pid,
                        channel_id="B2C",
                        quantity=round(qty * 0.03),
                        doc_type="return",
                    )
                )

    # --- 庫存快照(刻意讓部分品項庫存偏低,製造缺口示範) -------------------------
    stock_levels = {
        "RAW-BOTTLE-500": 3000,
        "RAW-PUMP": 2500,
        "RAW-OIL-SH": 60,       # 偏低,會觸發缺口
        "RAW-OIL-SG": 150,
        "RAW-BOX-GIFT": 200,    # 偏低
        "SEMI-SH-BULK": 40,     # 偏低
        "SEMI-SG-BULK": 120,
        "FG-SHAMPOO-500": 150,  # 偏低,會觸發缺口
        "FG-SHOWERGEL-500": 500,
        "COMBO-GIFTSET": 20,    # 偏低,會觸發缺口
        "FG-TRAVEL-SET": 15,
    }
    for pid, qty in stock_levels.items():
        db.add(models.InventoryDaily(snapshot_date=today, product_id=pid, quantity=qty))

    # --- 委外加工排程(ERP 匯入示範,供配送清單運算使用) --------------------------
    db.add_all(
        [
            models.ProcessingOrder(
                product_id="FG-SHAMPOO-500", plant_id="PLANT-FILL",
                planned_qty=800, required_date=today + timedelta(days=10),
            ),
            models.ProcessingOrder(
                product_id="FG-SHOWERGEL-500", plant_id="PLANT-FILL2",
                planned_qty=600, required_date=today + timedelta(days=14),
            ),
            models.ProcessingOrder(
                product_id="COMBO-GIFTSET", plant_id="PLANT-PACK",
                planned_qty=200, required_date=today + timedelta(days=20),
            ),
        ]
    )


if __name__ == "__main__":
    run()
