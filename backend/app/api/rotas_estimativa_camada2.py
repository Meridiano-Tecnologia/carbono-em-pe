"""
Carbono em Pé — Estimativa de nível 2 com equações alométricas regionais
Equações de Chave et al. 2005 (Global Ecology and Biogeography 14:677-688).
Pontuação de elegibilidade em quatro dimensões para mercado voluntário de carbono.
"""
import math
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from loguru import logger
from app.core.database import supabase


roteador = APIRouter(prefix="/estimativa", tags=["Estimativa"])


# ---------------------------------------------------------------------------
# Enumerações compartilhadas com a camada 1
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


class HistoricoDesmatamento(str, Enum):
    nenhum = "nenhum"
    baixo = "baixo"
    medio = "medio"
    alto = "alto"


# ---------------------------------------------------------------------------
# Parâmetros alométricos regionais — Chave et al. 2005
#
# Equação geral: AGB = exp(a + b × ln(DAP))
# onde DAP é o diâmetro à altura do peito em cm e AGB é a biomassa em kg.
#
# Para estimativas em escala de paisagem sem dados de inventário, os coeficientes
# são usados com um DAP médio representativo por bioma/tipo de vegetação.
# Referência: Chave et al. 2005, Tabelas 2 e 3 (zonas climáticas tropicais).
#
# Estrutura: (bioma, tipo_vegetacao) → (intercepto_a, coef_b, dap_medio_cm)
# ---------------------------------------------------------------------------

_PARAMETROS_ALOMETRICOS: dict[tuple[Bioma, TipoVegetacao], tuple[float, float, float]] = {
    # Amazônia — zona úmida tropical
    (Bioma.amazonia, TipoVegetacao.floresta_primaria):   (-1.499, 2.148, 38.0),
    (Bioma.amazonia, TipoVegetacao.floresta_secundaria): (-1.499, 2.148, 22.0),
    (Bioma.amazonia, TipoVegetacao.savana_arborizada):   (-1.499, 2.148, 14.0),

    # Cerrado — zona seca tropical (equação de zona seca, Tabela 3)
    (Bioma.cerrado, TipoVegetacao.floresta_primaria):    (-0.667, 1.784, 28.0),
    (Bioma.cerrado, TipoVegetacao.floresta_secundaria):  (-0.667, 1.784, 18.0),
    (Bioma.cerrado, TipoVegetacao.savana_arborizada):    (-0.667, 1.784, 12.0),
    (Bioma.cerrado, TipoVegetacao.campo_cerrado):        (-0.667, 1.784,  8.0),

    # Mata Atlântica — zona úmida tropical (mesmo grupo da Amazônia)
    (Bioma.mata_atlantica, TipoVegetacao.floresta_primaria):   (-1.499, 2.148, 34.0),
    (Bioma.mata_atlantica, TipoVegetacao.floresta_secundaria): (-1.499, 2.148, 20.0),
    (Bioma.mata_atlantica, TipoVegetacao.restinga):            (-1.499, 2.148, 12.0),
    (Bioma.mata_atlantica, TipoVegetacao.manguezal):           (-1.499, 2.148, 16.0),

    # Caatinga — zona seca tropical
    (Bioma.caatinga, TipoVegetacao.savana_arborizada): (-0.667, 1.784, 10.0),
    (Bioma.caatinga, TipoVegetacao.campo_cerrado):     (-0.667, 1.784,  7.0),

    # Pampa — zona seca subtropical
    (Bioma.pampa, TipoVegetacao.campo_cerrado): (-0.667, 1.784, 6.0),

    # Pantanal — zona úmida tropical
    (Bioma.pantanal, TipoVegetacao.savana_arborizada): (-1.499, 2.148, 13.0),
    (Bioma.pantanal, TipoVegetacao.manguezal):         (-1.499, 2.148, 15.0),
}

# Densidade de árvores representativa por tipo de vegetação (árvores/ha).
# Usada para escalar a biomassa individual para o nível de paisagem.
_DENSIDADE_ARVORES_HA: dict[TipoVegetacao, float] = {
    TipoVegetacao.floresta_primaria:   400.0,
    TipoVegetacao.floresta_secundaria: 600.0,
    TipoVegetacao.savana_arborizada:   180.0,
    TipoVegetacao.campo_cerrado:        80.0,
    TipoVegetacao.restinga:            150.0,
    TipoVegetacao.manguezal:           300.0,
}

# Fator raiz/parte aérea (root-to-shoot ratio) por tipo de vegetação.
# Valores médios de IPCC 2006 GL, Tabela 4.4.
_FATOR_RAIZ_PARTE_AEREA: dict[TipoVegetacao, float] = {
    TipoVegetacao.floresta_primaria:   0.24,
    TipoVegetacao.floresta_secundaria: 0.28,
    TipoVegetacao.savana_arborizada:   0.40,
    TipoVegetacao.campo_cerrado:       0.55,
    TipoVegetacao.restinga:            0.35,
    TipoVegetacao.manguezal:           0.30,
}

_FATOR_CARBONO = 0.47
_FATOR_CO2_EQUIVALENTE = 44 / 12

# Limites de classificação de elegibilidade
_LIMIAR_ALTO = 70.0
_LIMIAR_MEDIO = 40.0


# ---------------------------------------------------------------------------
# Modelos de entrada e saída
# ---------------------------------------------------------------------------

class EntradaCamada2(BaseModel):
    bioma: Bioma = Field(..., description="Bioma brasileiro onde a vegetação está localizada")
    tipo_vegetacao: TipoVegetacao = Field(..., description="Tipo de vegetação dominante na área")
    area_hectares: float = Field(..., gt=0, le=10_000_000, description="Área total em hectares")
    idade_anos: int = Field(..., ge=1, le=500, description="Idade estimada da vegetação em anos")
    presenca_reserva_legal: bool = Field(
        ...,
        description="A área está averbada como Reserva Legal no CAR",
    )
    app_regularizada: bool = Field(
        ...,
        description="As Áreas de Preservação Permanente estão regularizadas no CAR",
    )
    historico_desmatamento: HistoricoDesmatamento = Field(
        ...,
        description="Nível de pressão histórica de desmatamento na região",
    )
    tamanho_propriedade_ha: float = Field(
        ...,
        gt=0,
        le=50_000_000,
        description="Área total da propriedade em hectares (não apenas a vegetação)",
    )

    @field_validator("area_hectares", "tamanho_propriedade_ha")
    @classmethod
    def validar_precisao(cls, v: float) -> float:
        if round(v, 4) != v:
            raise ValueError("Áreas devem ter no máximo 4 casas decimais.")
        return v

    @field_validator("tamanho_propriedade_ha")
    @classmethod
    def validar_proporcao_area(cls, v: float, info) -> float:
        area = info.data.get("area_hectares")
        if area is not None and v < area:
            raise ValueError(
                "O tamanho da propriedade não pode ser menor que a área de vegetação informada."
            )
        return v


class PontuacaoDimensao(BaseModel):
    pontuacao: float = Field(..., ge=0, le=100)
    descricao: str


class ElegibilidadeCamada2(BaseModel):
    adicionalidade: PontuacaoDimensao
    permanencia: PontuacaoDimensao
    titularidade: PontuacaoDimensao
    tamanho: PontuacaoDimensao
    pontuacao_total: float
    classificacao: str


class ResultadoCamada2(BaseModel):
    bioma: str
    tipo_vegetacao: str
    area_hectares: float
    idade_anos: int
    dap_medio_cm: float
    biomassa_aerea_mg_ha: float
    biomassa_subterranea_mg_ha: float
    biomassa_total_mg: float
    carbono_total_mg: float
    co2_equivalente_t: float
    metodo: str
    elegibilidade: ElegibilidadeCamada2
    id_analise: str | None = None
    aviso: str | None = None


# ---------------------------------------------------------------------------
# Funções de cálculo
# ---------------------------------------------------------------------------

def _calcular_biomassa_alometrica(
    bioma: Bioma,
    tipo_vegetacao: TipoVegetacao,
    area_hectares: float,
) -> tuple[float, float, float, str | None]:
    """
    Retorna (biomassa_aerea_mg_ha, biomassa_subterranea_mg_ha, dap_medio, aviso).

    Equação de Chave et al. 2005:
        AGB_arvore (kg) = exp(a + b × ln(DAP))
    Escalonamento para paisagem:
        AGB_ha (Mg/ha) = AGB_arvore (kg) × densidade (árv/ha) / 1000
    Biomassa subterrânea = AGB_ha × fator_raiz_parte_aerea
    """
    chave = (bioma, tipo_vegetacao)
    parametros = _PARAMETROS_ALOMETRICOS.get(chave)
    aviso = None

    if parametros is None:
        # Fallback: médias dos parâmetros disponíveis
        todos_a = [p[0] for p in _PARAMETROS_ALOMETRICOS.values()]
        todos_b = [p[1] for p in _PARAMETROS_ALOMETRICOS.values()]
        todos_dap = [p[2] for p in _PARAMETROS_ALOMETRICOS.values()]
        a = sum(todos_a) / len(todos_a)
        b = sum(todos_b) / len(todos_b)
        dap = sum(todos_dap) / len(todos_dap)
        aviso = (
            "Combinação de bioma e tipo de vegetação sem parâmetros alométricos "
            "específicos em Chave et al. 2005. Foram usadas médias gerais como "
            "estimativa conservadora."
        )
        logger.warning(f"Parâmetros alométricos não encontrados para {chave} — usando médias gerais.")
    else:
        a, b, dap = parametros

    densidade_arvores = _DENSIDADE_ARVORES_HA.get(tipo_vegetacao, 200.0)
    fator_raiz = _FATOR_RAIZ_PARTE_AEREA.get(tipo_vegetacao, 0.30)

    agb_arvore_kg = math.exp(a + b * math.log(dap))
    biomassa_aerea_mg_ha = (agb_arvore_kg * densidade_arvores) / 1000.0
    biomassa_subterranea_mg_ha = biomassa_aerea_mg_ha * fator_raiz

    return biomassa_aerea_mg_ha, biomassa_subterranea_mg_ha, dap, aviso


def _calcular_elegibilidade(entrada: EntradaCamada2) -> ElegibilidadeCamada2:
    """
    Pontuação de elegibilidade em quatro dimensões (0–100 cada).
    Pontuação total = média simples das quatro dimensões.

    Dimensão 1 — Adicionalidade
      Avalia se a conservação da área vai além da obrigação legal.
      A presença de RL averbada e APP regularizada indica que o proprietário
      já cumpre a lei; a adicionalidade vem de área conservada além do mínimo legal.
      O histórico de desmatamento alto indica maior pressão e, portanto, maior
      adicionalidade potencial.

    Dimensão 2 — Permanência
      Avalia o risco de reversão do estoque de carbono.
      Histórico de desmatamento baixo e idade avançada da vegetação reduzem o risco.

    Dimensão 3 — Titularidade
      Avalia a clareza fundiária e conformidade ambiental.
      RL averbada e APP regularizada são os principais indicadores.

    Dimensão 4 — Tamanho
      Projetos muito pequenos têm alto custo de transação relativo;
      projetos acima de 500 ha são mais viáveis no mercado voluntário.
    """

    # -- Adicionalidade --
    pontos_adicionalidade = 50.0
    if entrada.presenca_reserva_legal:
        pontos_adicionalidade += 10.0
    if entrada.app_regularizada:
        pontos_adicionalidade += 10.0
    incremento_desmatamento = {
        HistoricoDesmatamento.nenhum: 0.0,
        HistoricoDesmatamento.baixo:  10.0,
        HistoricoDesmatamento.medio:  20.0,
        HistoricoDesmatamento.alto:   30.0,
    }
    pontos_adicionalidade += incremento_desmatamento[entrada.historico_desmatamento]
    pontos_adicionalidade = min(pontos_adicionalidade, 100.0)

    descricao_adicionalidade = (
        f"RL averbada: {'sim' if entrada.presenca_reserva_legal else 'não'} | "
        f"APP regularizada: {'sim' if entrada.app_regularizada else 'não'} | "
        f"Pressão de desmatamento: {entrada.historico_desmatamento.value}"
    )

    # -- Permanência --
    # Penalidade por risco de reversão: quanto maior o histórico de desmatamento,
    # maior o risco de perda futura do carbono estocado.
    penalidade_desmatamento = {
        HistoricoDesmatamento.nenhum: 0.0,
        HistoricoDesmatamento.baixo:  10.0,
        HistoricoDesmatamento.medio:  25.0,
        HistoricoDesmatamento.alto:   40.0,
    }
    # Bônus por idade: vegetação mais antiga tem maior estabilidade estrutural.
    bonus_idade = min(entrada.idade_anos / 2.0, 30.0)
    pontos_permanencia = 70.0 + bonus_idade - penalidade_desmatamento[entrada.historico_desmatamento]
    pontos_permanencia = max(0.0, min(pontos_permanencia, 100.0))

    descricao_permanencia = (
        f"Idade da vegetação: {entrada.idade_anos} anos | "
        f"Risco de reversão: {entrada.historico_desmatamento.value}"
    )

    # -- Titularidade --
    pontos_titularidade = 40.0
    if entrada.presenca_reserva_legal:
        pontos_titularidade += 30.0
    if entrada.app_regularizada:
        pontos_titularidade += 30.0
    pontos_titularidade = min(pontos_titularidade, 100.0)

    descricao_titularidade = (
        f"Conformidade CAR: {'completa' if entrada.presenca_reserva_legal and entrada.app_regularizada else 'parcial ou ausente'}"
    )

    # -- Tamanho --
    # Escala logarítmica: projetos maiores têm maior viabilidade econômica.
    # Referência: limiar mínimo de 50 ha; faixa ideal acima de 500 ha.
    if entrada.area_hectares < 50:
        pontos_tamanho = 10.0
    elif entrada.area_hectares < 200:
        pontos_tamanho = 30.0
    elif entrada.area_hectares < 500:
        pontos_tamanho = 55.0
    elif entrada.area_hectares < 2000:
        pontos_tamanho = 75.0
    elif entrada.area_hectares < 10000:
        pontos_tamanho = 90.0
    else:
        pontos_tamanho = 100.0

    descricao_tamanho = f"Área de vegetação: {entrada.area_hectares} ha"

    pontuacao_total = round(
        (pontos_adicionalidade + pontos_permanencia + pontos_titularidade + pontos_tamanho) / 4,
        2,
    )

    if pontuacao_total >= _LIMIAR_ALTO:
        classificacao = "alto"
    elif pontuacao_total >= _LIMIAR_MEDIO:
        classificacao = "medio"
    else:
        classificacao = "baixo"

    return ElegibilidadeCamada2(
        adicionalidade=PontuacaoDimensao(
            pontuacao=round(pontos_adicionalidade, 2),
            descricao=descricao_adicionalidade,
        ),
        permanencia=PontuacaoDimensao(
            pontuacao=round(pontos_permanencia, 2),
            descricao=descricao_permanencia,
        ),
        titularidade=PontuacaoDimensao(
            pontuacao=round(pontos_titularidade, 2),
            descricao=descricao_titularidade,
        ),
        tamanho=PontuacaoDimensao(
            pontuacao=round(pontos_tamanho, 2),
            descricao=descricao_tamanho,
        ),
        pontuacao_total=pontuacao_total,
        classificacao=classificacao,
    )


def _persistir_analise(entrada: EntradaCamada2, resultado: ResultadoCamada2) -> str | None:
    """
    Salva o resultado na tabela `analises` do Supabase.
    Retorna o id gerado pelo banco, ou None em caso de falha não crítica.
    """
    registro = {
        "metodo": "camada2",
        "bioma": entrada.bioma.value,
        "tipo_vegetacao": entrada.tipo_vegetacao.value,
        "area_hectares": entrada.area_hectares,
        "idade_anos": entrada.idade_anos,
        "presenca_reserva_legal": entrada.presenca_reserva_legal,
        "app_regularizada": entrada.app_regularizada,
        "historico_desmatamento": entrada.historico_desmatamento.value,
        "tamanho_propriedade_ha": entrada.tamanho_propriedade_ha,
        "biomassa_aerea_mg_ha": resultado.biomassa_aerea_mg_ha,
        "biomassa_subterranea_mg_ha": resultado.biomassa_subterranea_mg_ha,
        "biomassa_total_mg": resultado.biomassa_total_mg,
        "carbono_total_mg": resultado.carbono_total_mg,
        "co2_equivalente_t": resultado.co2_equivalente_t,
        "elegibilidade_adicionalidade": resultado.elegibilidade.adicionalidade.pontuacao,
        "elegibilidade_permanencia": resultado.elegibilidade.permanencia.pontuacao,
        "elegibilidade_titularidade": resultado.elegibilidade.titularidade.pontuacao,
        "elegibilidade_tamanho": resultado.elegibilidade.tamanho.pontuacao,
        "elegibilidade_pontuacao_total": resultado.elegibilidade.pontuacao_total,
        "elegibilidade_classificacao": resultado.elegibilidade.classificacao,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resposta = supabase.table("analises").insert(registro).execute()
        dados = resposta.data
        if dados and len(dados) > 0:
            id_gerado = str(dados[0].get("id", ""))
            logger.info(f"Análise camada 2 salva — id={id_gerado}")
            return id_gerado
    except Exception as erro:
        logger.error(f"Falha ao persistir análise camada 2: {erro}")

    return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@roteador.post(
    "/camada2",
    response_model=ResultadoCamada2,
    summary="Estimativa de tCO₂ com equações alométricas e pontuação de elegibilidade",
    response_description="Resultado com biomassa alométrica (Chave et al. 2005) e elegibilidade para mercado voluntário",
)
async def estimar_camada2(entrada: EntradaCamada2) -> JSONResponse:
    """
    Estima o estoque de carbono usando equações alométricas regionais de
    **Chave et al. 2005** e calcula uma pontuação de elegibilidade para o
    mercado voluntário de carbono em quatro dimensões:

    - **Adicionalidade** — conservação além da obrigação legal
    - **Permanência** — risco de reversão do estoque
    - **Titularidade** — conformidade fundiária e ambiental (CAR)
    - **Tamanho** — viabilidade econômica do projeto

    O resultado é salvo na tabela `analises` do Supabase.
    """
    biomassa_aerea, biomassa_subterranea, dap_medio, aviso = _calcular_biomassa_alometrica(
        entrada.bioma,
        entrada.tipo_vegetacao,
        entrada.area_hectares,
    )

    biomassa_total_mg_ha = biomassa_aerea + biomassa_subterranea
    biomassa_total_mg = biomassa_total_mg_ha * entrada.area_hectares
    carbono_total_mg = biomassa_total_mg * _FATOR_CARBONO
    co2_equivalente_t = carbono_total_mg * _FATOR_CO2_EQUIVALENTE

    elegibilidade = _calcular_elegibilidade(entrada)

    resultado = ResultadoCamada2(
        bioma=entrada.bioma.value,
        tipo_vegetacao=entrada.tipo_vegetacao.value,
        area_hectares=entrada.area_hectares,
        idade_anos=entrada.idade_anos,
        dap_medio_cm=round(dap_medio, 2),
        biomassa_aerea_mg_ha=round(biomassa_aerea, 4),
        biomassa_subterranea_mg_ha=round(biomassa_subterranea, 4),
        biomassa_total_mg=round(biomassa_total_mg, 4),
        carbono_total_mg=round(carbono_total_mg, 4),
        co2_equivalente_t=round(co2_equivalente_t, 4),
        metodo="Chave et al. 2005 — Equações alométricas regionais (Nível 2)",
        elegibilidade=elegibilidade,
        aviso=aviso,
    )

    resultado.id_analise = _persistir_analise(entrada, resultado)

    logger.info(
        f"Estimativa camada 2 | bioma={entrada.bioma} | area={entrada.area_hectares} ha | "
        f"tCO2={co2_equivalente_t:.2f} | elegibilidade={elegibilidade.classificacao} "
        f"({elegibilidade.pontuacao_total})"
    )

    return JSONResponse(content=resultado.model_dump())
