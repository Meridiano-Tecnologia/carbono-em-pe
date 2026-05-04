"""
Carbono em Pé — Rotas de autenticação
Login, refresh de token, logout e perfil do usuário autenticado.
"""
import traceback
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from loguru import logger
from app.core.database import supabase
from app.core.security import (
    verificar_senha,
    criar_token_acesso,
    criar_token_refresh,
    verificar_token,
    usuario_autenticado,
)


roteador = APIRouter(prefix="/auth", tags=["Autenticação"])

bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class EntradaLogin(BaseModel):
    email: EmailStr = Field(..., description="E-mail cadastrado do usuário")
    senha: str = Field(..., min_length=6, description="Senha do usuário")


class RespostaLogin(BaseModel):
    token_acesso: str
    token_refresh: str
    tipo: str = "Bearer"


class EntradaRefresh(BaseModel):
    token_refresh: str = Field(..., description="Token de refresh válido")


class RespostaRefresh(BaseModel):
    token_acesso: str
    tipo: str = "Bearer"


class RespostaPerfil(BaseModel):
    id: str
    nome: str
    email: str
    telefone: str | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@roteador.post(
    "/login",
    response_model=RespostaLogin,
    summary="Autentica o usuário e retorna tokens JWT",
    response_description="Tokens de acesso e refresh",
)
async def login(entrada: EntradaLogin) -> JSONResponse:
    """
    Verifica credenciais na tabela `usuarios` e emite par de tokens JWT.
    Retorna 401 para credenciais inválidas — nunca revela qual campo falhou.
    """
    try:
        resultado = (
            supabase.table("usuarios")
            .select("id, nome, email, telefone, senha_hash")
            .eq("email", entrada.email)
            .limit(1)
            .execute()
        )

        usuario = resultado.data[0] if resultado.data else None

        # Verificação em tempo constante para evitar timing attacks
        senha_hash_comparacao = usuario["senha_hash"] if usuario else "$2b$12$invalido_para_comparacao_segura"
        credenciais_validas = verificar_senha(entrada.senha, senha_hash_comparacao)

        if not usuario or not credenciais_validas:
            logger.warning(f"Tentativa de login falhou | email={entrada.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha incorretos.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = {"sub": str(usuario["id"]), "email": usuario["email"]}
        token_acesso = criar_token_acesso(payload)
        token_refresh = criar_token_refresh(payload)

        logger.info(f"Login bem-sucedido | usuario_id={usuario['id']}")

        return JSONResponse(
            content=RespostaLogin(
                token_acesso=token_acesso,
                token_refresh=token_refresh,
            ).model_dump()
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(f"Erro inesperado no login | email={entrada.email}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno na autenticação. Tente novamente.",
        )


@roteador.post(
    "/refresh",
    response_model=RespostaRefresh,
    summary="Renova o token de acesso usando o token de refresh",
    response_description="Novo token de acesso",
)
async def renovar_token(entrada: EntradaRefresh) -> JSONResponse:
    """
    Valida o token de refresh e emite um novo token de acesso.
    O token de refresh permanece válido até seu vencimento natural.
    """
    try:
        payload = verificar_token(entrada.token_refresh, tipo="refresh")

        usuario_id = payload.get("sub")
        email = payload.get("email")

        if not usuario_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Confirma que o usuário ainda existe e está ativo
        resultado = (
            supabase.table("usuarios")
            .select("id")
            .eq("id", usuario_id)
            .limit(1)
            .execute()
        )
        if not resultado.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado ou inativo.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        novo_token = criar_token_acesso({"sub": usuario_id, "email": email})
        logger.info(f"Token renovado | usuario_id={usuario_id}")

        return JSONResponse(
            content=RespostaRefresh(token_acesso=novo_token).model_dump()
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(f"Erro ao renovar token\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao renovar token. Tente novamente.",
        )


@roteador.post(
    "/logout",
    summary="Encerra a sessão do usuário autenticado",
    response_description="Confirmação de logout",
)
async def logout(
    payload: dict = Depends(usuario_autenticado),
) -> JSONResponse:
    """
    Invalida a sessão atual do usuário.
    O cliente deve descartar os tokens armazenados localmente.
    Como os tokens JWT são stateless, a invalidação definitiva exige
    que o cliente os descarte — tokens expiram no prazo configurado.
    """
    usuario_id = payload.get("sub", "desconhecido")
    logger.info(f"Logout | usuario_id={usuario_id}")

    return JSONResponse(
        content={"mensagem": "Sessão encerrada com sucesso. Descarte os tokens armazenados."}
    )


@roteador.get(
    "/eu",
    response_model=RespostaPerfil,
    summary="Retorna os dados do usuário autenticado",
    response_description="Perfil do usuário logado",
)
async def meu_perfil(
    payload: dict = Depends(usuario_autenticado),
) -> JSONResponse:
    """
    Rota protegida — exige token de acesso válido no cabeçalho Authorization.
    Retorna os dados públicos do perfil do usuário logado.
    """
    try:
        usuario_id = payload.get("sub")

        resultado = (
            supabase.table("usuarios")
            .select("id, nome, email, telefone")
            .eq("id", usuario_id)
            .limit(1)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )

        usuario = resultado.data[0]
        logger.info(f"Perfil consultado | usuario_id={usuario_id}")

        return JSONResponse(
            content=RespostaPerfil(
                id=str(usuario["id"]),
                nome=usuario["nome"],
                email=usuario["email"],
                telefone=usuario.get("telefone"),
            ).model_dump()
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(f"Erro ao buscar perfil | usuario_id={payload.get('sub')}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao buscar perfil. Tente novamente.",
        )
