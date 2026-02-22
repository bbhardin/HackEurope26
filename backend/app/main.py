from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_URL
from app.routers import health, orders, webhook, nudge, customers, alerts, activity, simulate, products

app = FastAPI(title="Wholesaler AI Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(orders.router)
app.include_router(nudge.router)
app.include_router(customers.router)
app.include_router(alerts.router)
app.include_router(activity.router)
app.include_router(simulate.router)
app.include_router(products.router)
