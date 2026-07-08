from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_tables
from app.routes import articles, health, lookup, search, statistics


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Retraction Watch API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(articles.router)
app.include_router(lookup.router)
app.include_router(search.router)
app.include_router(statistics.router)
