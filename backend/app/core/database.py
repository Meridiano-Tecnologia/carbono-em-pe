"""
Carbono em Pé — Conexão com Supabase
Service role key usada APENAS no backend, nunca exposta ao frontend.
"""
from supabase import create_client, Client
from app.core.config import settings
from loguru import logger


def criar_cliente_supabase() -> Client:
    """
    Cria cliente Supabase com service role key.
    Usado apenas em operações server-side seguras.
    """
    try:
        logger.info(f"Chave service role (primeiros 20 chars): {settings.SUPABASE_SERVICE_ROLE_KEY[:20]}")
        cliente = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        logger.info("Conexão com Supabase estabelecida com sucesso.")
        return cliente
    except Exception as e:
        logger.error(f"Erro ao conectar com Supabase: {e}")
        raise


def criar_cliente_publico() -> Client:
    """
    Cria cliente Supabase com anon key.
    Usado para operações que respeitam RLS — seguras para dados do usuário.
    """
    try:
        cliente = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        return cliente
    except Exception as e:
        logger.error(f"Erro ao criar cliente público Supabase: {e}")
        raise


# Instâncias reutilizáveis
supabase: Client = criar_cliente_supabase()
supabase_publico: Client = criar_cliente_publico()
