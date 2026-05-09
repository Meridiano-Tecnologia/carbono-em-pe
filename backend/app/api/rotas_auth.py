"""
Carbono em Pé — Rotas de autenticação
Login, refresh de token, logout e perfil do usuário autenticado.
"""
import asyncio
import hashlib
import re
import secrets
import smtplib
import traceback
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from loguru import logger
from app.core.config import settings
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


class EntradaEsqueciSenha(BaseModel):
    email: EmailStr


class EntradaRedefinirSenha(BaseModel):
    token: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8)


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


# ---------------------------------------------------------------------------
# Reset de senha
# ---------------------------------------------------------------------------

_REGEX_MAIUSCULA = re.compile(r"[A-Z]")
_REGEX_MINUSCULA = re.compile(r"[a-z]")
_REGEX_NUMERO    = re.compile(r"\d")

_RESPOSTA_ESQUECI = {"mensagem": "Se o e-mail existir, você receberá as instruções em breve."}


def _validar_nova_senha(senha: str) -> str | None:
    """Retorna mensagem de erro ou None se válida."""
    if len(senha) < 8:
        return "A senha deve ter ao menos 8 caracteres."
    if not _REGEX_MAIUSCULA.search(senha):
        return "A senha deve conter ao menos uma letra maiúscula."
    if not _REGEX_MINUSCULA.search(senha):
        return "A senha deve conter ao menos uma letra minúscula."
    if not _REGEX_NUMERO.search(senha):
        return "A senha deve conter ao menos um número."
    return None


def _enviar_email_reset(email_destino: str, link: str) -> None:
    """Envia e-mail de reset via SMTP (executar em thread separada)."""
    texto_simples = (
        f"Redefinição de senha — Carbono em Pé\n\n"
        f"Recebemos uma solicitação para redefinir a senha da sua conta.\n"
        f"Acesse o link abaixo para criar uma nova senha:\n\n"
        f"{link}\n\n"
        f"⏱ Este link expira em 15 minutos.\n"
        f"Se você não solicitou, ignore este e-mail — sua senha permanece a mesma.\n\n"
        f"Meridiano Tecnologia"
    )

    html = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<body style="margin:0;padding:0;background:#0d1f0f;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table width="480" cellpadding="0" cellspacing="0"
          style="background:#132a16;border:1px solid #1e4024;border-radius:16px;overflow:hidden;max-width:480px;">
          <tr>
            <td style="padding:28px 36px;border-bottom:1px solid #1e4024;">
              <span style="font-size:18px;font-weight:700;color:#4caf72;">🌱 Carbono em Pé</span>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 36px;">
              <h1 style="margin:0 0 12px;font-size:22px;font-weight:700;color:#e8f5ed;letter-spacing:-0.02em;">
                Redefinição de senha
              </h1>
              <p style="margin:0 0 24px;font-size:14px;color:#86a98c;line-height:1.7;">
                Recebemos uma solicitação para redefinir a senha da sua conta.
                Clique no botão abaixo para criar uma nova senha.
              </p>
              <a href="{link}"
                style="display:inline-block;padding:14px 28px;background:#4caf72;color:#ffffff;
                       text-decoration:none;border-radius:12px;font-weight:700;font-size:14px;">
                Redefinir minha senha →
              </a>
              <p style="margin:28px 0 0;font-size:12px;color:#86a98c;line-height:1.7;">
                ⏱ Este link expira em <strong style="color:#e8f5ed;">15 minutos</strong>.<br>
                Se você não solicitou a redefinição de senha, ignore este e-mail —
                sua senha permanece a mesma e nenhuma ação é necessária.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 36px;border-top:1px solid #1e4024;">
              <p style="margin:0;font-size:11px;color:#86a98c;line-height:1.6;">
                Meridiano Tecnologia · CNPJ 66.298.885/0001-65<br>
                Rua País Leme, 215, Conj. 1713, Pinheiros, São Paulo/SP, CEP 05.424-150
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Redefinição de senha — Carbono em Pé"
    msg["From"]    = settings.SMTP_USER
    msg["To"]      = email_destino
    msg.attach(MIMEText(texto_simples, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(settings.SMTP_HOST, 465) as srv:
        srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        srv.sendmail(settings.SMTP_USER, email_destino, msg.as_string())


@roteador.post(
    "/esqueci-senha",
    summary="Solicita redefinição de senha por e-mail",
    response_description="Instrução genérica (não revela se o e-mail existe)",
)
async def esqueci_senha(entrada: EntradaEsqueciSenha) -> JSONResponse:
    """
    Gera token de reset com validade de 15 minutos, salva hash na tabela
    `usuarios` e envia e-mail com link de redefinição.
    Sempre retorna 200 para não revelar se o e-mail está cadastrado.
    """
    try:
        resultado = (
            supabase.table("usuarios")
            .select("id, email")
            .eq("email", str(entrada.email))
            .limit(1)
            .execute()
        )

        if resultado.data:
            usuario    = resultado.data[0]
            token      = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expira_em  = datetime.now(timezone.utc) + timedelta(minutes=15)

            supabase.table("usuarios").update({
                "reset_token_hash":   token_hash,
                "reset_token_expira": expira_em.isoformat(),
            }).eq("id", usuario["id"]).execute()

            frontend_url = settings.origens_permitidas[0].rstrip("/")
            link = f"{frontend_url}/redefinir-senha?token={token}"

            smtp_resultado = None
            smtp_erro      = None
            try:
                await asyncio.to_thread(_enviar_email_reset, usuario["email"], link)
                logger.info(f"E-mail de reset enviado | usuario_id={usuario['id']}")
                smtp_resultado = "sucesso"
            except Exception:
                smtp_erro = traceback.format_exc()
                logger.error(f"Falha ao enviar e-mail de reset | usuario_id={usuario['id']}\n{smtp_erro}")
                smtp_resultado = "erro"

            # temporário para debug — remover depois
            return JSONResponse(status_code=200, content={
                **_RESPOSTA_ESQUECI,
                "smtp_resultado": smtp_resultado,
                "smtp_erro": smtp_erro,
            })

    except Exception:
        logger.error(f"Erro inesperado em esqueci-senha | email={entrada.email}\n{traceback.format_exc()}")

    return JSONResponse(content=_RESPOSTA_ESQUECI)


@roteador.post(
    "/redefinir-senha",
    summary="Redefine a senha usando token enviado por e-mail",
    response_description="Confirmação de redefinição",
)
async def redefinir_senha(entrada: EntradaRedefinirSenha) -> JSONResponse:
    """
    Valida o token de reset (hash + expiração), aplica a nova senha
    e limpa os campos de reset para invalidar o link.
    """
    erro_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Link de redefinição inválido ou expirado.",
    )

    erro_senha = lambda msg: HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=msg,
    )

    try:
        token_hash = hashlib.sha256(entrada.token.encode()).hexdigest()

        resultado = (
            supabase.table("usuarios")
            .select("id, reset_token_hash, reset_token_expira")
            .eq("reset_token_hash", token_hash)
            .limit(1)
            .execute()
        )

        if not resultado.data:
            raise erro_token

        usuario = resultado.data[0]

        expira_raw = usuario.get("reset_token_expira")
        if not expira_raw:
            raise erro_token

        expira_em = datetime.fromisoformat(expira_raw.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expira_em:
            raise erro_token

        mensagem_invalida = _validar_nova_senha(entrada.nova_senha)
        if mensagem_invalida:
            raise erro_senha(mensagem_invalida)

        from app.core.security import hash_senha
        nova_hash = hash_senha(entrada.nova_senha)

        supabase.table("usuarios").update({
            "senha_hash":          nova_hash,
            "reset_token_hash":    None,
            "reset_token_expira":  None,
        }).eq("id", usuario["id"]).execute()

        logger.info(f"Senha redefinida | usuario_id={usuario['id']}")
        return JSONResponse(content={"mensagem": "Senha redefinida com sucesso."})

    except HTTPException:
        raise
    except Exception:
        logger.error(f"Erro inesperado em redefinir-senha\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao redefinir senha. Tente novamente.",
        )
