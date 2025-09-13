# app/main.py
import logging
import time
from typing import List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import DuplicateKeyError

from app.db import connect_to_mongo, close_mongo_connection, settings

logger = logging.getLogger("uvicorn.error")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLUMO_SDE1 - Employee API",
        description="Employee management API (FastAPI + MongoDB)",
        version="0.1.0",
    )

    allow_origins: List[str] = []
    try:
        raw = getattr(settings, "ALLOWED_ORIGINS", None)
        if raw:
            if isinstance(raw, str):
                allow_origins = [o.strip() for o in raw.split(",") if o.strip()]
            elif isinstance(raw, (list, tuple)):
                allow_origins = list(raw)
    except Exception:
        allow_origins = []

    if not allow_origins:
        allow_origins = ["*"] 

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
            process_time = (time.time() - start) * 1000
            logger.info(
                f"{request.method} {request.url.path} completed_in={process_time:.2f}ms status_code={response.status_code}"
            )
            return response
        except Exception as exc:
            process_time = (time.time() - start) * 1000
            logger.exception(
                f"{request.method} {request.url.path} errored_in={process_time:.2f}ms exc={exc}"
            )
            raise

    # Register startup/shutdown tasks
    @app.on_event("startup")
    async def startup() -> None:
        logger.info("Starting app - connecting to MongoDB")
        await connect_to_mongo()

        # create indexes if repository exposes a helper
        try:
            # import lazily so app can start even if repo not implemented yet
            from app.repositories.employee_repo import create_indexes as repo_create_indexes
            try:
                await repo_create_indexes()
                logger.info("Database indexes ensured by employee_repo.create_indexes()")
            except Exception as e:
                logger.warning("Failed to create indexes via employee_repo.create_indexes(): %s", e)
        except Exception:
            logger.debug("No employee_repo.create_indexes() found; skipping index creation.")

        logger.info("Startup complete")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        logger.info("Shutting down app - closing MongoDB connection")
        await close_mongo_connection()
        logger.info("Shutdown complete")

    # Global exception handlers
    @app.exception_handler(DuplicateKeyError)
    async def duplicate_key_exception_handler(request: Request, exc: DuplicateKeyError):
        return JSONResponse(status_code=400, content={"detail": "Duplicate key error: resource already exists"})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log the exception and return 500
        logger.exception("Unhandled exception occurred: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    # Health endpoint
    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}
    try:
        from app.routes.employee_routes import router as employee_router

        app.include_router(employee_router, prefix="/employees", tags=["employees"])
        logger.info("Employee router included at /employees")
    except Exception as e:
        logger.warning("Employee router not included (import failed): %s", e)
    try:
        from app.routes.auth import router as auth_router

        app.include_router(auth_router, prefix="/auth", tags=["auth"])
        logger.info("Auth router included at /auth")
    except Exception:
        logger.debug("Auth router not included (not implemented)")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True, log_level="info")
