from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import create_tables, ensure_fts
from app.homepages import API_HOMEPAGE
from app.routes import articles, health, lookup, search, statistics


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    ensure_fts()
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def homepage() -> HTMLResponse:
    return HTMLResponse(API_HOMEPAGE)


app.include_router(health.router)
app.include_router(articles.router)
app.include_router(lookup.router)
app.include_router(search.router)
app.include_router(statistics.router)
