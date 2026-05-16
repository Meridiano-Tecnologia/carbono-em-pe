"""
Carbono em Pé — Rotas de pagamento
Integração Stripe: criação de sessão, webhook e consulta de status.
"""
import asyncio
import traceback
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger
from app.core.config import settings
from app.core.database import supabase
from app.core.security import usuario_autenticado
from app.services.gerador_pdf import gerar_relatorio_pdf


stripe.api_key = settings.STRIPE_SECRET_KEY

roteador = APIRouter(prefix="/pagamento", tags=["Pagamento"])


# ---------------------------------------------------------------------------
# Precificação
# ---------------------------------------------------------------------------

_PRECO_CAMADA2_CENTAVOS = 1900  # R$ 19,00

# Faixas para camada 3: (área máxima em ha, valor em centavos)
# Área None ou ≤ 50 ha → R$ 19 | acima de 500 ha → sob consulta (None)
_FAIXAS_CAMADA3 = [
    (50,  1_900),   # até 50 ha       → R$  19
    (200, 6_900),   # 51 a 200 ha     → R$  69
    (500, 12_900),  # 201 a 500 ha    → R$ 129
]


def _calcular_valor_camada3(area_hectares: float | None) -> int | None:
    """Retorna o valor em centavos ou None quando a área exige orçamento sob consulta."""
    area = area_hectares or 0.0
    for limite, valor in _FAIXAS_CAMADA3:
        if area <= limite:
            return valor
    return None  # acima de 500 ha → sob consulta


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class EntradaCriarSessao(BaseModel):
    analise_id: str = Field(..., description="ID da análise vinculada ao pagamento")
    camada: int = Field(..., ge=1, le=4, description="Camada de análise (1 a 4)")
    area_hectares: float | None = Field(
        default=None,
        gt=0,
        description="Área em hectares — usada para precificação da camada 3 (opcional)",
    )


class RespostaSessao(BaseModel):
    url_checkout: str
    valor_centavos: int
    gratuito: bool


class RespostaStatus(BaseModel):
    analise_id: str
    status: str
    valor_centavos: int | None
    stripe_session_id: str | None


class RespostaSessaoPorId(BaseModel):
    valor_centavos: int
    status: str
    camada: int
    criado_em: str | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@roteador.post(
    "/criar-sessao",
    response_model=RespostaSessao,
    summary="Cria sessão de pagamento no Stripe",
    response_description="URL do checkout Stripe e valor cobrado",
)
async def criar_sessao(
    entrada: EntradaCriarSessao,
    payload: dict = Depends(usuario_autenticado),
) -> JSONResponse:
    """
    Calcula o valor conforme a camada, cria sessão Stripe e registra em `pagamentos`.

    - Camada 1: gratuita, confirmada automaticamente.
    - Camada 2: R$ 19,00 fixo.
    - Camada 3: R$ 19 a R$ 129 conforme `area_hectares`.
    - Camada 4: orçamento personalizado — retorna erro orientando contato direto.
    """
    if entrada.camada == 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A camada 4 exige orçamento personalizado. "
                "Entre em contato com a Meridiano Tecnologia para combinar o valor diretamente."
            ),
        )

    if entrada.camada == 1:
        valor_centavos = 0
    elif entrada.camada == 2:
        valor_centavos = _PRECO_CAMADA2_CENTAVOS
    else:
        valor_calculado = _calcular_valor_camada3(entrada.area_hectares)
        if valor_calculado is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Propriedades com área acima de 500 ha requerem orçamento personalizado. "
                    "Entre em contato com a Meridiano Tecnologia para combinar o valor diretamente."
                ),
            )
        valor_centavos = valor_calculado

    usuario_id = payload.get("sub")

    try:
        # Camada gratuita — confirma direto, sem sessão Stripe
        if valor_centavos == 0:
            supabase.table("pagamentos").insert({
                "analise_id": entrada.analise_id,
                "usuario_id": usuario_id,
                "camada": entrada.camada,
                "valor_centavos": 0,
                "status": "confirmado",
                "stripe_session_id": None,
            }).execute()

            logger.info(
                f"Análise gratuita confirmada | analise_id={entrada.analise_id} | usuario_id={usuario_id}"
            )
            return JSONResponse(
                content=RespostaSessao(
                    url_checkout="",
                    valor_centavos=0,
                    gratuito=True,
                ).model_dump()
            )

        # Camadas pagas — cria sessão Stripe
        url_base = settings.origens_permitidas[0].rstrip("/")

        metodos = ["card", "pix"] if settings.STRIPE_PIX_ENABLED else ["card"]
        opcoes_metodo = {"pix": {"expires_after_seconds": 1800}} if settings.STRIPE_PIX_ENABLED else {}

        sessao = stripe.checkout.Session.create(
            payment_method_types=metodos,
            **({"payment_method_options": opcoes_metodo} if opcoes_metodo else {}),
            line_items=[{
                "price_data": {
                    "currency": "brl",
                    "unit_amount": valor_centavos,
                    "product_data": {
                        "name": f"Carbono em Pé — Análise Camada {entrada.camada}",
                        "description": (
                            f"Diagnóstico de estoque de carbono em biomassa aérea "
                            f"— análise #{entrada.analise_id}"
                        ),
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{url_base}/pagamento/sucesso?sessao={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{url_base}/pagamento/cancelado",
            metadata={
                "analise_id": entrada.analise_id,
                "usuario_id": usuario_id,
                "camada": str(entrada.camada),
            },
        )

        supabase.table("pagamentos").insert({
            "analise_id": entrada.analise_id,
            "usuario_id": usuario_id,
            "camada": entrada.camada,
            "valor_centavos": valor_centavos,
            "status": "pendente",
            "stripe_session_id": sessao.id,
        }).execute()

        logger.info(
            f"Sessão Stripe criada | analise_id={entrada.analise_id} "
            f"| session_id={sessao.id} | valor={valor_centavos}c"
        )

        return JSONResponse(
            content=RespostaSessao(
                url_checkout=sessao.url,
                valor_centavos=valor_centavos,
                gratuito=False,
            ).model_dump()
        )

    except stripe.StripeError as e:
        logger.error(
            f"Erro Stripe ao criar sessão | analise_id={entrada.analise_id} "
            f"| http_status={e.http_status} | code={getattr(e, 'code', None)} "
            f"| param={getattr(e, 'param', None)} | mensagem={e.user_message or str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao comunicar com o serviço de pagamento. Tente novamente.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.error(
            f"Erro inesperado ao criar sessão | analise_id={entrada.analise_id}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar pagamento. Tente novamente.",
        )


@roteador.post(
    "/webhook",
    include_in_schema=False,
    summary="Recebe eventos do Stripe (uso interno)",
)
async def webhook_stripe(request: Request) -> JSONResponse:
    """
    Endpoint exclusivo para o Stripe — não autenticado por JWT.
    Valida assinatura HMAC com STRIPE_WEBHOOK_SECRET antes de processar.
    Em `checkout.session.completed` atualiza o pagamento para 'confirmado'
    e dispara a geração do relatório.
    """
    corpo_bruto = await request.body()
    assinatura = request.headers.get("stripe-signature", "")

    try:
        evento = stripe.Webhook.construct_event(
            corpo_bruto, assinatura, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        logger.warning("Webhook Stripe com assinatura inválida — requisição rejeitada.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assinatura do webhook inválida.",
        )
    except Exception:
        logger.error(f"Erro ao construir evento Stripe\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload do webhook inválido.",
        )

    if evento["type"] == "checkout.session.completed":
        sessao = evento["data"]["object"]
        session_id = sessao.get("id")
        metadados = sessao.get("metadata", {})
        analise_id = metadados.get("analise_id")
        camada = metadados.get("camada", "1")

        try:
            supabase.table("pagamentos").update({
                "status": "confirmado",
            }).eq("stripe_session_id", session_id).execute()

            logger.info(
                f"Pagamento confirmado via webhook | session_id={session_id} "
                f"| analise_id={analise_id} | camada={camada}"
            )

            if camada == "2":
                await _disparar_calculo_camada2(analise_id, session_id)
            else:
                await _disparar_geracao_relatorio(analise_id)

        except Exception:
            # Retorna 200 mesmo em falha interna para evitar reenvios infinitos do Stripe
            logger.error(
                f"Erro ao processar evento confirmed | session_id={session_id}\n{traceback.format_exc()}"
            )

    return JSONResponse(content={"recebido": True})


async def _disparar_calculo_camada2(analise_id: str | None, session_id: str) -> None:
    """
    Após pagamento de Camada 2 confirmado:
    1. Busca o registro analise_id → obtém propriedade_id
    2. Busca propriedades → parâmetros de vegetação
    3. Roda cálculo alométrico (Chave et al. 2005) e pontuação de elegibilidade
    4. Insere novo registro em analises com camada=2
    5. Gera o PDF da nova análise

    Parâmetros de elegibilidade não armazenados (presenca_reserva_legal,
    app_regularizada, historico_desmatamento) usam defaults conservadores —
    isso é registrado em log para futura revisão.
    """
    if not analise_id:
        logger.warning(f"Calculo Camada 2: analise_id ausente | session_id={session_id}")
        return

    try:
        # 1. Obtém propriedade_id a partir da análise de Camada 1
        analise_resp = await asyncio.to_thread(
            lambda: supabase.table("analises")
            .select("propriedade_id")
            .eq("id", analise_id)
            .limit(1)
            .execute()
        )
        if not analise_resp.data:
            logger.error(
                f"Calculo Camada 2: análise {analise_id} não encontrada | session_id={session_id}"
            )
            return

        propriedade_id = analise_resp.data[0].get("propriedade_id")
        if not propriedade_id:
            logger.error(
                f"Calculo Camada 2: propriedade_id ausente na análise {analise_id}"
            )
            return

        # 2. Obtém parâmetros de vegetação da propriedade
        prop_resp = await asyncio.to_thread(
            lambda: supabase.table("propriedades")
            .select("bioma, tipo_vegetacao, area_vegetacao_ha, idade_vegetacao_anos, area_total_ha")
            .eq("id", str(propriedade_id))
            .limit(1)
            .execute()
        )
        if not prop_resp.data:
            logger.error(
                f"Calculo Camada 2: propriedade {propriedade_id} não encontrada | analise_id={analise_id}"
            )
            return

        prop = prop_resp.data[0]

        # 3. Cálculo alométrico e elegibilidade (importação local para evitar ciclo de import)
        from app.api.rotas_estimativa_camada2 import (  # noqa: PLC0415
            _calcular_biomassa_alometrica,
            _calcular_elegibilidade,
            Bioma,
            TipoVegetacao,
            HistoricoDesmatamento,
            EntradaCamada2,
            _FATOR_CARBONO,
            _FATOR_CO2_EQUIVALENTE,
        )

        bioma      = Bioma(prop["bioma"])
        tipo_veg   = TipoVegetacao(prop["tipo_vegetacao"])
        area_ha    = float(prop["area_vegetacao_ha"])
        idade      = int(prop["idade_vegetacao_anos"])
        area_total = float(prop["area_total_ha"])

        biomassa_aerea, biomassa_sub, _dap, aviso = _calcular_biomassa_alometrica(
            bioma, tipo_veg, area_ha
        )
        biomassa_total_mg = (biomassa_aerea + biomassa_sub) * area_ha
        co2_t = biomassa_total_mg * _FATOR_CARBONO * _FATOR_CO2_EQUIVALENTE

        # presenca_reserva_legal / app_regularizada / historico_desmatamento não são
        # armazenados em propriedades — usamos defaults conservadores
        entrada_eleg = EntradaCamada2(
            bioma=bioma,
            tipo_vegetacao=tipo_veg,
            area_hectares=area_ha,
            idade_anos=idade,
            presenca_reserva_legal=False,
            app_regularizada=False,
            historico_desmatamento=HistoricoDesmatamento.baixo,
            tamanho_propriedade_ha=area_total,
        )
        elegibilidade = _calcular_elegibilidade(entrada_eleg)

        logger.warning(
            f"Calculo Camada 2 usou defaults conservadores para elegibilidade "
            f"(RL/APP/desmatamento não armazenados) | propriedade_id={propriedade_id}"
        )

        # 4. Insere análise Camada 2
        nova_analise = await asyncio.to_thread(
            lambda: supabase.table("analises").insert({
                "propriedade_id":    str(propriedade_id),
                "camada":            2,
                "status":            "concluido",
                "tco2_estimado":     round(co2_t, 4),
                "biomassa_tha":      round(biomassa_total_mg / area_ha, 4),
                "score_adicionalidade": elegibilidade.adicionalidade.pontuacao,
                "score_permanencia":    elegibilidade.permanencia.pontuacao,
                "score_titularidade":   elegibilidade.titularidade.pontuacao,
                "score_tamanho":        elegibilidade.tamanho.pontuacao,
                "elegibilidade":        elegibilidade.classificacao,
                "metodo_calculo":    "chave_2005",
                "versao_algoritmo":  "1.0.0",
            }).execute()
        )

        dados = nova_analise.data
        if not dados:
            logger.error(
                f"Calculo Camada 2: insert em analises não retornou dados | propriedade_id={propriedade_id}"
            )
            return

        novo_analise_id = str(dados[0]["id"])
        if aviso:
            logger.warning(f"Aviso no cálculo alométrico Camada 2 | {aviso}")

        logger.info(
            f"Análise Camada 2 criada via webhook | novo_analise_id={novo_analise_id} "
            f"| analise_origem={analise_id} | propriedade_id={propriedade_id} "
            f"| tco2={co2_t:.2f} | elegibilidade={elegibilidade.classificacao} "
            f"| session_id={session_id}"
        )

        # 5. Gera PDF da nova análise Camada 2
        await _disparar_geracao_relatorio(novo_analise_id)

    except Exception:
        logger.error(
            f"Falha no cálculo Camada 2 | analise_id={analise_id} | session_id={session_id}\n"
            f"{traceback.format_exc()}"
        )


async def _disparar_geracao_relatorio(analise_id: str | None) -> None:
    """
    Gera o PDF da análise, faz upload no Supabase Storage e atualiza
    a tabela analises com a URL pública. Nunca propaga exceções.
    Operações bloqueantes rodam em thread separada para não travar o event loop.
    """
    if not analise_id:
        logger.warning("Webhook sem analise_id nos metadados — relatório não disparado.")
        return

    caminho_storage = f"relatorios/{analise_id}.pdf"

    try:
        pdf_bytes: bytes = await asyncio.to_thread(gerar_relatorio_pdf, analise_id)
        logger.info(f"PDF gerado | analise_id={analise_id} | tamanho={len(pdf_bytes):,} bytes")
    except Exception:
        logger.error(
            f"Falha ao gerar PDF | analise_id={analise_id}\n{traceback.format_exc()}"
        )
        return

    try:
        await asyncio.to_thread(
            lambda: supabase.storage
            .from_(settings.SUPABASE_STORAGE_BUCKET)
            .upload(
                caminho_storage,
                pdf_bytes,
                {"content-type": "application/pdf", "upsert": "true"},
            )
        )
        logger.info(
            f"PDF enviado ao Storage | bucket={settings.SUPABASE_STORAGE_BUCKET} "
            f"| caminho={caminho_storage}"
        )
    except Exception:
        logger.error(
            f"Falha ao enviar PDF ao Storage | analise_id={analise_id}\n{traceback.format_exc()}"
        )
        return

    try:
        url_publica: str = supabase.storage.from_(
            settings.SUPABASE_STORAGE_BUCKET
        ).get_public_url(caminho_storage)

        await asyncio.to_thread(
            lambda: supabase.table("analises")
            .update({"url_relatorio_pdf": url_publica})
            .eq("id", analise_id)
            .execute()
        )
        logger.info(
            f"URL do relatório salva | analise_id={analise_id} | url={url_publica}"
        )
    except Exception:
        logger.error(
            f"Falha ao salvar URL do relatório na tabela analises | analise_id={analise_id}\n"
            f"{traceback.format_exc()}"
        )


@roteador.get(
    "/sessao/{sessao_id}",
    response_model=RespostaSessaoPorId,
    summary="Consulta pagamento pelo ID de sessão Stripe",
    response_description="Dados do pagamento vinculado à sessão",
)
async def pagamento_por_sessao(
    sessao_id: str,
    payload: dict = Depends(usuario_autenticado),
) -> JSONResponse:
    """
    Busca o pagamento pelo stripe_session_id.
    Usuário só pode consultar pagamentos da sua própria conta.
    """
    usuario_id = payload.get("sub")

    try:
        resultado = (
            supabase.table("pagamentos")
            .select("usuario_id, valor_centavos, status, camada, criado_em")
            .eq("stripe_session_id", sessao_id)
            .limit(1)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pagamento não encontrado para esta sessão.",
            )

        registro = resultado.data[0]

        if registro["usuario_id"] != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso não autorizado.",
            )

        return JSONResponse(
            content=RespostaSessaoPorId(
                valor_centavos=registro["valor_centavos"],
                status=registro["status"],
                camada=registro["camada"],
                criado_em=str(registro["criado_em"]) if registro.get("criado_em") else None,
            ).model_dump()
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(f"Erro ao consultar sessão | sessao_id={sessao_id}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar o pagamento.",
        )


@roteador.get(
    "/status/{analise_id}",
    response_model=RespostaStatus,
    summary="Consulta o status do pagamento de uma análise",
    response_description="Status atual do pagamento vinculado à análise",
)
async def status_pagamento(
    analise_id: str,
    payload: dict = Depends(usuario_autenticado),
) -> JSONResponse:
    """
    Retorna o status do pagamento da análise informada.
    Usuário só pode consultar pagamentos vinculados à sua própria conta.
    """
    usuario_id = payload.get("sub")

    try:
        resultado = (
            supabase.table("pagamentos")
            .select("analise_id, status, valor_centavos, stripe_session_id, usuario_id")
            .eq("analise_id", analise_id)
            .limit(1)
            .execute()
        )

        if not resultado.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum pagamento encontrado para a análise '{analise_id}'.",
            )

        registro = resultado.data[0]

        if registro["usuario_id"] != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso não autorizado ao pagamento desta análise.",
            )

        return JSONResponse(
            content=RespostaStatus(
                analise_id=registro["analise_id"],
                status=registro["status"],
                valor_centavos=registro.get("valor_centavos"),
                stripe_session_id=registro.get("stripe_session_id"),
            ).model_dump()
        )

    except HTTPException:
        raise
    except Exception:
        logger.error(
            f"Erro ao consultar status | analise_id={analise_id}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar status do pagamento.",
        )
