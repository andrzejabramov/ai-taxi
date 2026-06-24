import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from loguru import logger
from .request_id import request_id_ctx


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request_id_ctx.get()
        start_time = time.time()

        logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={"request_id": request_id},
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(
                f"[{request_id}] {response.status_code} ({process_time:.3f}s)",
                extra={"request_id": request_id},
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] 500 ({process_time:.3f}s) | {e}",
                extra={"request_id": request_id},
            )
            raise
