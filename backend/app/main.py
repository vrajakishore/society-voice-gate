import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, tickets, webhooks

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Society Voice Gate",
    version="1.0.0",
    description="AI voice agent that answers resident calls and auto-creates maintenance tickets.",
)

# SECURITY: Wildcard CORS is acceptable for local dev / demo only.
# For production, restrict to your frontend domain(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(tickets.router)
app.include_router(health.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
