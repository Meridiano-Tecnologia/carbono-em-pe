"""
Carbono em Pé — Ponto de entrada da aplicação
Meridiano Tecnologia
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.middleware import configurar_middleware
from app.api.rotas_estimativa import roteador as roteador_estimativa
from loguru import logger
import sys


# Configuração de logging estruturado
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level=settings.LOG_LEVEL,
    colorize=True
)
logger.add(
    "logs/carbono_em_pe.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="WARNING",
    rotation="10 MB",
    retention="30 days",
    compression="zip"
)


# Inicialização da aplicação
app = FastAPI(
    title="Carbono em Pé",
    description="Plataforma de diagnóstico de estoque de carbono em biomassa aérea — Meridiano Tecnologia",
    version="0.1.0",
    docs_url="/docs" if settings.is_development() else None,
    redoc_url="/redoc" if settings.is_development() else None,
    openapi_url="/openapi.json" if settings.is_development() else None,
)

# Middlewares de segurança
configurar_middleware(app)

# Rotas
app.include_router(roteador_estimativa)


@app.on_event("startup")
async def startup():
    logger.info("Carbono em Pé iniciando...")
    logger.info(f"Ambiente: {settings.APP_ENV}")
    if settings.is_production():
        logger.info("Documentação desabilitada — ambiente de produção.")
    logger.info("Aplicação pronta.")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Carbono em Pé encerrando...")


@app.get("/", include_in_schema=False)
async def raiz():
    return JSONResponse(
        content={
            "produto": "Carbono em Pé",
            "empresa": "Meridiano Tecnologia",
            "versao": "0.1.0",
            "status": "operacional"
        }
    )


@app.get("/saude", include_in_schema=False)
async def verificar_saude():
    """Endpoint de health check — usado pelo Railway para monitoramento."""
    return JSONResponse(
        content={"status": "saudavel"}
    )
