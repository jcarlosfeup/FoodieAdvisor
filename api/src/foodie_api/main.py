"""FastAPI application factory. Run locally with `uv run foodie-api` (docs at /docs)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from foodie_api.repository import PostgresRepository, Repository
from foodie_api.routers import health, places, restaurants
from foodie_api.settings import ApiHttpSettings, ApiSettings
from foodie_common.db import make_engine
from foodie_common.logging import configure_logging


def create_app(settings: ApiSettings | None = None, repository: Repository | None = None) -> FastAPI:
    """Build the app. Settings and the repository are resolved at startup unless injected (tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings or ApiSettings()
        engine = None
        if repository is None:
            engine = make_engine(app.state.settings, pool_size=5, max_overflow=5)
            app.state.repository = PostgresRepository(engine)
        else:
            app.state.repository = repository
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="FoodieAdvisor API",
        version="0.1.0",
        description=(
            "Read-only API for traditional restaurants by city. Restaurant data © OpenStreetMap "
            "contributors (ODbL); city data © GeoNames (CC BY 4.0)."
        ),
        lifespan=lifespan,
    )
    cors_origins = (settings or ApiHttpSettings()).api_cors_origins
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET"], allow_headers=["*"])
    app.include_router(health.router)
    app.include_router(places.router)
    app.include_router(restaurants.router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    configure_logging()
    settings = ApiSettings()
    uvicorn.run("foodie_api.main:app", host=settings.api_host, port=settings.api_port, log_config=None)
