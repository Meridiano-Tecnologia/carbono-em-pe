"""
Carbono em Pé — Rotas de diagnóstico de saúde dos serviços
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.database import supabase
from loguru import logger


roteador = APIRouter(prefix="/saude", tags=["Saúde"])


@roteador.get(
    "/banco",
    summary="Diagnóstico de conexão com o banco de dados",
    response_description="Estado da conexão com o Supabase e total de registros na tabela de usuários",
)
async def verificar_banco() -> JSONResponse:
    """
    Testa a conexão com o Supabase contando os registros da tabela `usuarios`.
    Retorna status `conectado` e o total de registros, ou `erro` com a mensagem de falha.
    """
    try:
        resposta = supabase.table("usuarios").select("*", count="exact").limit(0).execute()
        total = resposta.count if resposta.count is not None else 0

        logger.info(f"Diagnóstico do banco concluído — total de usuários: {total}")

        return JSONResponse(
            content={
                "status": "conectado",
                "tabela": "usuarios",
                "total_registros": total,
            }
        )
    except Exception as erro:
        logger.error(f"Falha no diagnóstico do banco: {erro}")

        return JSONResponse(
            status_code=503,
            content={
                "status": "erro",
                "mensagem": str(erro),
            },
        )
