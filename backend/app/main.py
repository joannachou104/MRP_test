from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401  ensure models are registered before create_all
from app.routers import (
    products,
    bom,
    suppliers,
    plants,
    channels,
    sales,
    inventory,
    imports,
    mrp,
    procurement,
    ignore,
    processing_orders,
    distribution,
    users,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="客製化 MRP 系統(本機測試版)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    products.router,
    bom.router,
    suppliers.router,
    plants.router,
    channels.router,
    sales.router,
    inventory.router,
    imports.router,
    mrp.router,
    procurement.router,
    ignore.router,
    processing_orders.router,
    distribution.router,
    users.router,
):
    app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
