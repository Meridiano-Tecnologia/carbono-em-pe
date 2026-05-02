"""
Carbono em Pé — Middleware de segurança
Headers de segurança implementados manualmente — sem dependências externas.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from app.core.config import settings
import time
import uuid

limiter = Limiter(key_func=get_remote_address)


def configurar_middleware(app: FastAPI) -> None:

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origens_permitidas,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler
    )

    @app.middleware("http")
    async def middleware_seguranca(request: Request, call_next):
        request_id = str(uuid.uuid4())
        inicio = time.time()

        if not request.headers.get("user-agent"):
            logger.warning(f"Bloqueado — sem User-Agent | IP: {get_remote_address(request)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Requisição inválida."}
            )

        response = await call_next(request)

        # Headers de segurança manuais
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        response.headers["X-Request-ID"] = request_id
        response.headers["Server"] = ""
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        duracao = round((time.time() - inicio) * 1000, 2)
        logger.info(
            f"{request.method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Duração: {duracao}ms | "
            f"IP: {get_remote_address(request)} | "
            f"ID: {request_id}"
        )

        return response
