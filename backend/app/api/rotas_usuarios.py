"""
Carbono em Pé — Rotas de cadastro de usuários e propriedades
"""
import re
import traceback
from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from enum import Enum
from loguru import logger
from app.core.database import supabase
from app.core.security import hash_senha


roteador = APIRouter(prefix="/usuarios", tags=["Usuários"])


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class Bioma(str, Enum):
    amazonia = "Amazônia"
    cerrado = "Cerrado"
    mata_atlantica = "Mata Atlântica"
    caatinga = "Caatinga"
    pampa = "Pampa"
    pantanal = "Pantanal"


class TipoVegetacao(str, Enum):
    floresta_primaria = "Floresta primária"
    floresta_secundaria = "Floresta secundária"
    savana_arborizada = "Savana arborizada"
    campo_cerrado = "Campo cerrado"
    restinga = "Restinga"
    manguezal = "Manguezal"


# ---------------------------------------------------------------------------
# Modelos — cadastro de usuário
# ---------------------------------------------------------------------------

class EntradaConsentimento(BaseModel):
    tipo: str
    aceito: bool
    obrigatorio: bool
    texto_exibido: str


class EntradaCadastroUsuario(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="Endereço de e-mail — deve ser único")
    senha: str = Field(
        ...,
        min_length=8,
        description="Senha com mínimo de 8 caracteres, uma maiúscula, uma minúscula e um número",
    )
    telefone: str | None = Field(
        default=None,
        min_length=8,
        max_length=20,
        description="Telefone com DDD, somente dígitos (opcional)",
    )
    consentimentos: List[EntradaConsentimento] = []

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
        if not re.search(r"[a-z]", v):
            raise ValueError("A senha deve conter ao menos uma letra minúscula.")
        if not re.search(r"\d", v):
            raise ValueError("A senha deve conter ao menos um número.")
        return v

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) < 8:
            raise ValueError("O telefone deve conter ao menos 8 dígitos.")
        return apenas_digitos


class RespostaCadastroUsuario(BaseModel):
    id: str
    mensagem: str


# ---------------------------------------------------------------------------
# Modelos — cadastro de propriedade
# ---------------------------------------------------------------------------

class EntradaCadastroPropriedade(BaseModel):
    usuario_id: UUID = Field(..., description="UUID do usuário dono da propriedade")
    nome_propriedade: str = Field(..., min_length=2, max_length=300, description="Nome da propriedade rural")
    bioma: Bioma = Field(..., description="Bioma predominante da propriedade")
    area_total_ha: float = Field(..., gt=0, le=50_000_000, description="Área total da propriedade em hectares")
    area_vegetacao_ha: float = Field(..., gt=0, le=50_000_000, description="Área de vegetação nativa em hectares")
    tipo_vegetacao: TipoVegetacao = Field(..., description="Tipo de vegetação dominante")
    idade_vegetacao_anos: int = Field(..., ge=1, le=500, description="Idade estimada da vegetação em anos")
    codigo_car: str | None = Field(
        default=None,
        min_length=10,
        max_length=100,
        description="Código CAR da propriedade — deve ser único quando informado",
    )

    @field_validator("area_total_ha", "area_vegetacao_ha")
    @classmethod
    def validar_precisao(cls, v: float) -> float:
        if round(v, 4) != v:
            raise ValueError("Áreas devem ter no máximo 4 casas decimais.")
        return v

    @field_validator("area_vegetacao_ha")
    @classmethod
    def validar_vegetacao_menor_que_total(cls, v: float, info) -> float:
        total = info.data.get("area_total_ha")
        if total is not None and v > total:
            raise ValueError(
                "A área de vegetação não pode ser maior que a área total da propriedade."
            )
        return v

    @field_validator("codigo_car")
    @classmethod
    def normalizar_car(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().upper()


class RespostaCadastroPropriedade(BaseModel):
    id: str
    mensagem: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@roteador.post(
    "/cadastrar",
    response_model=RespostaCadastroUsuario,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário",
    response_description="ID do usuário criado",
)
async def cadastrar_usuario(entrada: EntradaCadastroUsuario, request: Request) -> JSONResponse:
    """
    Cria um novo usuário na tabela `usuarios`.
    Retorna erro 409 se o e-mail já estiver cadastrado.
    """
    try:
        duplicado = (
            supabase.table("usuarios")
            .select("id")
            .eq("email", entrada.email)
            .limit(1)
            .execute()
        )
        if duplicado.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um usuário cadastrado com o e-mail '{entrada.email}'.",
            )

        senha_hash = hash_senha(entrada.senha)

        novo = (
            supabase.table("usuarios")
            .insert({
                "nome": entrada.nome,
                "email": entrada.email,
                "telefone": entrada.telefone,
                "senha_hash": senha_hash,
            })
            .execute()
        )

        id_gerado = str(novo.data[0]["id"])
        logger.info(f"Usuário cadastrado — id={id_gerado} | email={entrada.email}")

        if entrada.consentimentos:
            try:
                registros = [
                    {
                        "usuario_id": id_gerado,
                        "tipo": c.tipo,
                        "aceito": c.aceito,
                        "obrigatorio": c.obrigatorio,
                        "texto_exibido": c.texto_exibido,
                        "ip_address": request.client.host if request.client else None,
                        "user_agent": request.headers.get("user-agent"),
                    }
                    for c in entrada.consentimentos
                ]
                supabase.table("consentimentos").insert(registros).execute()
                logger.info(f"Consentimentos registrados — usuario_id={id_gerado} | total={len(registros)}")
            except Exception:
                logger.error(
                    f"Falha ao salvar consentimentos — usuario_id={id_gerado}\n{traceback.format_exc()}"
                )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=RespostaCadastroUsuario(
                id=id_gerado,
                mensagem="Usuário cadastrado com sucesso.",
            ).model_dump(),
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(
            f"Falha ao cadastrar usuário | email={entrada.email}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao cadastrar o usuário. Tente novamente.",
        )


@roteador.post(
    "/propriedade",
    response_model=RespostaCadastroPropriedade,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma propriedade rural vinculada a um usuário",
    response_description="ID da propriedade criada",
)
async def cadastrar_propriedade(entrada: EntradaCadastroPropriedade) -> JSONResponse:
    """
    Cria um novo registro na tabela `propriedades` vinculado ao usuário informado.
    Retorna erro 404 se o usuário não existir, 409 se o código CAR já estiver cadastrado.
    """
    try:
        usuario = (
            supabase.table("usuarios")
            .select("id")
            .eq("id", str(entrada.usuario_id))
            .limit(1)
            .execute()
        )
        if not usuario.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuário com id '{entrada.usuario_id}' não encontrado.",
            )

        if entrada.codigo_car is not None:
            duplicado = (
                supabase.table("propriedades")
                .select("id")
                .eq("codigo_car", entrada.codigo_car)
                .limit(1)
                .execute()
            )
            if duplicado.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Já existe uma propriedade cadastrada com o código CAR '{entrada.codigo_car}'.",
                )

        nova = (
            supabase.table("propriedades")
            .insert({
                "usuario_id": str(entrada.usuario_id),
                "nome_propriedade": entrada.nome_propriedade,
                "bioma": entrada.bioma.value,
                "area_total_ha": entrada.area_total_ha,
                "area_vegetacao_ha": entrada.area_vegetacao_ha,
                "tipo_vegetacao": entrada.tipo_vegetacao.value,
                "idade_vegetacao_anos": entrada.idade_vegetacao_anos,
                "codigo_car": entrada.codigo_car,
            })
            .execute()
        )

        id_gerado = str(nova.data[0]["id"])
        logger.info(
            f"Propriedade cadastrada — id={id_gerado} | usuario_id={entrada.usuario_id} "
            f"| nome='{entrada.nome_propriedade}'"
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=RespostaCadastroPropriedade(
                id=id_gerado,
                mensagem="Propriedade cadastrada com sucesso.",
            ).model_dump(),
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(
            f"Falha ao cadastrar propriedade | usuario_id={entrada.usuario_id}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao cadastrar a propriedade. Tente novamente.",
        )
