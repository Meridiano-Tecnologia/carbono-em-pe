"""
Carbono em Pé — Segurança e autenticação
JWT com expiração curta, refresh token e verificação rigorosa.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from loguru import logger

# Contexto de criptografia — bcrypt é o padrão mais seguro
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de autenticação Bearer
bearer_scheme = HTTPBearer()


def hash_senha(senha: str) -> str:
    """Gera hash seguro da senha com bcrypt."""
    return pwd_context.hash(senha)


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Verifica senha contra hash armazenado."""
    return pwd_context.verify(senha_plana, senha_hash)


def criar_token_acesso(dados: dict) -> str:
    """
    Cria JWT de acesso com expiração curta (30 minutos).
    Nunca inclua dados sensíveis no payload.
    """
    payload = dados.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({
        "exp": expiracao,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def criar_token_refresh(dados: dict) -> str:
    """
    Cria JWT de refresh com expiração maior (7 dias).
    Usado apenas para renovar o token de acesso.
    """
    payload = dados.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload.update({
        "exp": expiracao,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def verificar_token(token: str, tipo: str = "access") -> dict:
    """
    Verifica e decodifica JWT.
    Valida tipo do token para evitar uso indevido de refresh como access.
    """
    excecao = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != tipo:
            raise excecao
        return payload
    except JWTError as e:
        logger.warning(f"Tentativa de acesso com token inválido: {e}")
        raise excecao


async def usuario_autenticado(
    credenciais: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Dependência FastAPI — protege rotas autenticadas.
    Uso: adicionar como parâmetro na rota com Depends(usuario_autenticado)
    """
    return verificar_token(credenciais.credentials, tipo="access")
