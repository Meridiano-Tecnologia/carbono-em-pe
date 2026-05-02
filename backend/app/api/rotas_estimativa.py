"""
Carbono em Pé — Rotas de estimativa de estoque de carbono
Método de nível 1 do IPCC com fator de conversão biomassa-carbono de 0,47.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from loguru import logger


roteador = APIRouter(prefix="/estimativa", tags=["Estimativa"])


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


# Densidade de biomassa acima do solo em Mg/ha por bioma e tipo de vegetação.
# Valores de referência: IPCC 2006 GL, tabelas 4.7 e 4.8 (Tabela de nível 1).
_DENSIDADE_BIOMASSA: dict[tuple[Bioma, TipoVegetacao], float] = {
    (Bioma.amazonia, TipoVegetacao.floresta_primaria): 300.0,
    (Bioma.amazonia, TipoVegetacao.floresta_secundaria): 180.0,
    (Bioma.amazonia, TipoVegetacao.savana_arborizada): 80.0,
    (Bioma.cerrado, TipoVegetacao.floresta_primaria): 115.0,
    (Bioma.cerrado, TipoVegetacao.floresta_secundaria): 80.0,
    (Bioma.cerrado, TipoVegetacao.savana_arborizada): 52.0,
    (Bioma.cerrado, TipoVegetacao.campo_cerrado): 28.0,
    (Bioma.mata_atlantica, TipoVegetacao.floresta_primaria): 250.0,
    (Bioma.mata_atlantica, TipoVegetacao.floresta_secundaria): 140.0,
    (Bioma.mata_atlantica, TipoVegetacao.restinga): 60.0,
    (Bioma.mata_atlantica, TipoVegetacao.manguezal): 120.0,
    (Bioma.caatinga, TipoVegetacao.savana_arborizada): 40.0,
    (Bioma.caatinga, TipoVegetacao.campo_cerrado): 20.0,
    (Bioma.pampa, TipoVegetacao.campo_cerrado): 15.0,
    (Bioma.pantanal, TipoVegetacao.savana_arborizada): 55.0,
    (Bioma.pantanal, TipoVegetacao.manguezal): 110.0,
}

# Fator de conversão de biomassa para carbono (IPCC 2006, seção 2.3.2)
_FATOR_CARBONO = 0.47

# Fator de conversão de carbono para CO₂ equivalente (razão molar 44/12)
_FATOR_CO2_EQUIVALENTE = 44 / 12


class EntradaCamada1(BaseModel):
    bioma: Bioma = Field(
        ...,
        description="Bioma brasileiro onde a vegetação está localizada",
    )
    tipo_vegetacao: TipoVegetacao = Field(
        ...,
        description="Tipo de vegetação dominante na área",
    )
    area_hectares: float = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="Área total da vegetação em hectares",
    )
    idade_anos: int = Field(
        ...,
        ge=1,
        le=500,
        description="Idade estimada da vegetação em anos",
    )

    @field_validator("area_hectares")
    @classmethod
    def validar_area(cls, v: float) -> float:
        if round(v, 4) != v:
            raise ValueError("A área deve ter no máximo 4 casas decimais.")
        return v


class ResultadoCamada1(BaseModel):
    bioma: str
    tipo_vegetacao: str
    area_hectares: float
    idade_anos: int
    densidade_biomassa_mg_ha: float
    biomassa_total_mg: float
    carbono_total_mg: float
    co2_equivalente_t: float
    metodo: str
    aviso: str | None = None


@roteador.post(
    "/camada1",
    response_model=ResultadoCamada1,
    summary="Estimativa de tCO₂ pelo método de nível 1 do IPCC",
    response_description="Resultado do cálculo de estoque de carbono em tCO₂ equivalente",
)
async def estimar_camada1(entrada: EntradaCamada1) -> JSONResponse:
    """
    Estima o estoque de carbono (em tCO₂ equivalente) com base nos dados
    autodeclarados do usuário, usando o método de nível 1 do IPCC.

    **Fórmula aplicada:**
    1. Biomassa total (Mg) = área (ha) × densidade de biomassa (Mg/ha)
    2. Carbono total (Mg) = biomassa total × 0,47
    3. CO₂ equivalente (t) = carbono total × (44/12)

    Os fatores de densidade provêm das tabelas de referência do IPCC 2006 GL,
    capítulo 4 (Florestas).
    """
    chave = (entrada.bioma, entrada.tipo_vegetacao)
    densidade = _DENSIDADE_BIOMASSA.get(chave)

    aviso = None
    if densidade is None:
        # Combinação não catalogada: aplica média geral das densidades disponíveis
        densidade = sum(_DENSIDADE_BIOMASSA.values()) / len(_DENSIDADE_BIOMASSA)
        aviso = (
            "A combinação de bioma e tipo de vegetação informada não possui fator "
            "de densidade específico nas tabelas IPCC 2006 GL. Foi aplicada a média "
            "geral como estimativa conservadora. Recomenda-se revisão com dados de campo."
        )
        logger.warning(
            f"Combinação sem fator IPCC: bioma={entrada.bioma}, "
            f"tipo_vegetacao={entrada.tipo_vegetacao} — usando média geral ({densidade:.2f} Mg/ha)"
        )

    biomassa_total = entrada.area_hectares * densidade
    carbono_total = biomassa_total * _FATOR_CARBONO
    co2_equivalente = carbono_total * _FATOR_CO2_EQUIVALENTE

    logger.info(
        f"Estimativa camada 1 calculada | bioma={entrada.bioma} | "
        f"area={entrada.area_hectares} ha | tCO2={co2_equivalente:.2f}"
    )

    return JSONResponse(
        content=ResultadoCamada1(
            bioma=entrada.bioma.value,
            tipo_vegetacao=entrada.tipo_vegetacao.value,
            area_hectares=entrada.area_hectares,
            idade_anos=entrada.idade_anos,
            densidade_biomassa_mg_ha=round(densidade, 4),
            biomassa_total_mg=round(biomassa_total, 4),
            carbono_total_mg=round(carbono_total, 4),
            co2_equivalente_t=round(co2_equivalente, 4),
            metodo="IPCC 2006 GL — Nível 1 (Tabelas 4.7 e 4.8)",
            aviso=aviso,
        ).model_dump()
    )
