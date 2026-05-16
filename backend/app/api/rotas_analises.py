"""
Carbono em Pé — Rotas de consulta de análises do usuário
"""
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger
from app.core.database import supabase
from app.core.security import usuario_autenticado


roteador = APIRouter(prefix="/analises", tags=["Análises"])


class RespostaAnalise(BaseModel):
    id: str
    camada: int | None
    status: str | None
    tco2_estimado: float | None
    biomassa_tha: float | None
    elegibilidade: str | None
    metodo_calculo: str | None
    criado_em: str | None
    nome_propriedade: str | None
    bioma: str | None


@roteador.get(
    "/minhas",
    response_model=list[RespostaAnalise],
    summary="Lista todas as análises do usuário autenticado",
    response_description="Lista ordenada da mais recente para a mais antiga",
)
async def listar_minhas_analises(
    usuario: dict = Depends(usuario_autenticado),
) -> list[RespostaAnalise]:
    """
    Retorna todas as análises vinculadas ao usuário logado,
    com o nome da propriedade e bioma obtidos via join.
    Retorna lista vazia se o usuário não tiver análises.
    """
    usuario_id: str = usuario.get("sub")
    if not usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: identificador do usuário ausente.",
        )

    try:
        # A tabela analises não tem usuario_id diretamente — o vínculo é via propriedade_id.
        # Buscamos primeiro os IDs das propriedades do usuário para depois filtrar as análises.
        props = (
            supabase.table("propriedades")
            .select("id")
            .eq("usuario_id", usuario_id)
            .execute()
        )
        ids_propriedades = [str(p["id"]) for p in props.data]

        if not ids_propriedades:
            logger.info(f"Sem propriedades — usuario_id={usuario_id}")
            return []

        resultado = (
            supabase.table("analises")
            .select(
                "id, camada, status, tco2_estimado, biomassa_tha, "
                "elegibilidade, metodo_calculo, criado_em, "
                "propriedades(nome_propriedade, bioma)"
            )
            .in_("propriedade_id", ids_propriedades)
            .order("criado_em", desc=True)
            .execute()
        )

        analises: list[RespostaAnalise] = []
        for linha in resultado.data:
            prop = linha.get("propriedades") or {}
            analises.append(
                RespostaAnalise(
                    id=str(linha["id"]),
                    camada=linha.get("camada"),
                    status=linha.get("status"),
                    tco2_estimado=linha.get("tco2_estimado"),
                    biomassa_tha=linha.get("biomassa_tha"),
                    elegibilidade=linha.get("elegibilidade"),
                    metodo_calculo=linha.get("metodo_calculo"),
                    criado_em=str(linha["criado_em"]) if linha.get("criado_em") else None,
                    nome_propriedade=prop.get("nome_propriedade"),
                    bioma=prop.get("bioma"),
                )
            )

        logger.info(
            f"Análises listadas — usuario_id={usuario_id} | total={len(analises)}"
        )
        return analises

    except HTTPException:
        raise
    except Exception:
        logger.error(
            f"Falha ao listar análises | usuario_id={usuario_id}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao buscar as análises. Tente novamente.",
        )


@roteador.get(
    "/{analise_id}",
    response_model=RespostaAnalise,
    summary="Busca uma análise pelo ID",
    response_description="Dados da análise solicitada",
)
async def buscar_analise(
    analise_id: str,
    usuario: dict = Depends(usuario_autenticado),
) -> RespostaAnalise:
    """
    Retorna os dados de uma análise específica.
    Usuário só pode acessar análises vinculadas à sua própria conta.
    O parâmetro analise_id é tratado como string para aceitar qualquer formato de UUID.
    """
    usuario_id: str = usuario.get("sub")
    if not usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: identificador do usuário ausente.",
        )

    try:
        resultado = (
            supabase.table("analises")
            .select(
                "id, camada, status, tco2_estimado, biomassa_tha, "
                "elegibilidade, metodo_calculo, criado_em, "
                "propriedades(nome_propriedade, bioma, usuario_id)"
            )
            .eq("id", analise_id)
            .limit(1)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Análise '{analise_id}' não encontrada.",
            )

        linha = resultado.data[0]
        prop = linha.get("propriedades") or {}

        if prop.get("usuario_id") != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso não autorizado a esta análise.",
            )

        logger.info(f"Análise consultada | analise_id={analise_id} | usuario_id={usuario_id}")

        return RespostaAnalise(
            id=str(linha["id"]),
            camada=linha.get("camada"),
            status=linha.get("status"),
            tco2_estimado=linha.get("tco2_estimado"),
            biomassa_tha=linha.get("biomassa_tha"),
            elegibilidade=linha.get("elegibilidade"),
            metodo_calculo=linha.get("metodo_calculo"),
            criado_em=str(linha["criado_em"]) if linha.get("criado_em") else None,
            nome_propriedade=prop.get("nome_propriedade"),
            bioma=prop.get("bioma"),
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(
            f"Falha ao buscar análise | analise_id={analise_id}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao buscar a análise. Tente novamente.",
        )
