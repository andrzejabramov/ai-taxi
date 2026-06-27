from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.middleware.request_id import RequestIDMiddleware
from src.middleware.logging import LoggingMiddleware
from src.db.pools import init_pools, close_pools
from src.routers import chat, geo, trips, speech
from src.logger_config import setup_logger
from src.exceptions.base import ValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация/закрытие пулов БД"""
    logger.info("🚀 Initializing taxi-agent service...")
    setup_logger()
    await init_pools()
    logger.info("✅ Database pools initialized")
    yield
    logger.info("🛑 Shutting down taxi-agent service...")
    await close_pools()
    logger.info("✅ Database pools closed")


app = FastAPI(
    title="Taxi Agent Service",
    description="Корпоративный агент заказа такси",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(geo.router, prefix="/api/v1")
app.include_router(trips.router, prefix="/api/v1")
app.include_router(speech.router, prefix="/api/v1")


# Exception handlers
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logger.warning(f"Validation error: {exc.message}", extra={"details": exc.details})
    return JSONResponse(
        status_code=400, content={"detail": exc.message, "details": exc.details}
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
