"""
Carbono em Pé — Gerador de relatório em PDF
Busca dados da análise no Supabase, monta HTML e converte com WeasyPrint.

Dependência de sistema:
  Linux  (Railway): apt-get install -y libpango-1.0-0 libcairo2
  macOS  (dev):     DYLD_LIBRARY_PATH=$(brew --prefix)/lib uvicorn ...
"""
import io
from datetime import date
from loguru import logger
from weasyprint import HTML as WeasyHTML
from app.core.database import supabase


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------

def gerar_relatorio_pdf(analise_id: str) -> bytes:
    """
    Busca a análise, junta dados da propriedade e do usuário,
    renderiza HTML e retorna os bytes do PDF.
    Lança ValueError se a análise não for encontrada.
    """
    dados = _buscar_dados(analise_id)
    html = _montar_html(dados)
    return _converter_para_pdf(html)


# ---------------------------------------------------------------------------
# Busca de dados
# ---------------------------------------------------------------------------

def _buscar_dados(analise_id: str) -> dict:
    resp_analise = (
        supabase.table("analises")
        .select(
            "id, camada, status, tco2_estimado, biomassa_tha, "
            "score_adicionalidade, score_permanencia, score_titularidade, score_tamanho, "
            "elegibilidade, metodo_calculo, versao_algoritmo, criado_em, propriedade_id"
        )
        .eq("id", analise_id)
        .limit(1)
        .execute()
    )
    if not resp_analise.data:
        raise ValueError(f"Análise '{analise_id}' não encontrada.")

    analise = resp_analise.data[0]
    propriedade_id = analise.get("propriedade_id")

    propriedade: dict = {}
    usuario: dict = {}

    if propriedade_id:
        resp_prop = (
            supabase.table("propriedades")
            .select(
                "id, nome_propriedade, bioma, area_total_ha, area_vegetacao_ha, "
                "tipo_vegetacao, idade_vegetacao_anos, codigo_car, usuario_id"
            )
            .eq("id", str(propriedade_id))
            .limit(1)
            .execute()
        )
        if resp_prop.data:
            propriedade = resp_prop.data[0]
            usuario_id = propriedade.get("usuario_id")
            if usuario_id:
                resp_usr = (
                    supabase.table("usuarios")
                    .select("nome, email")
                    .eq("id", str(usuario_id))
                    .limit(1)
                    .execute()
                )
                if resp_usr.data:
                    usuario = resp_usr.data[0]

    return {"analise": analise, "propriedade": propriedade, "usuario": usuario}


# ---------------------------------------------------------------------------
# Montagem do HTML
# ---------------------------------------------------------------------------

_COR_VERDE_ESCURO = "#1a5c2e"
_COR_VERDE_MEDIO = "#2d8c4e"
_COR_VERDE_CLARO = "#e8f5ed"
_COR_TEXTO = "#1a1a1a"
_COR_BORDA = "#c8dfd0"


def _barra_pontuacao(pontuacao: float, cor: str = _COR_VERDE_MEDIO) -> str:
    pct = max(0.0, min(float(pontuacao), 100.0))
    return f"""
    <div class="barra-container">
        <div class="barra-preenchida" style="width:{pct:.1f}%; background:{cor};"></div>
    </div>
    <span class="barra-valor">{pct:.0f} / 100</span>"""


def _cor_elegibilidade(classificacao: str) -> str:
    return {"alto": "#1a5c2e", "medio": "#b45309", "baixo": "#991b1b"}.get(
        classificacao.lower(), _COR_VERDE_ESCURO
    )


def _label_elegibilidade(classificacao: str) -> str:
    return {"alto": "Alta", "medio": "Média", "baixo": "Baixa"}.get(
        classificacao.lower(), classificacao.capitalize()
    )


def _formatar_numero(valor, casas: int = 2, unidade: str = "") -> str:
    if valor is None:
        return "—"
    try:
        formatado = f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatado} {unidade}".strip()
    except (TypeError, ValueError):
        return str(valor)


def _montar_html(dados: dict) -> str:
    analise = dados["analise"]
    prop = dados["propriedade"]
    usuario = dados["usuario"]

    data_geracao = date.today().strftime("%d/%m/%Y")
    analise_id_curto = str(analise.get("id", ""))[:8].upper()

    tco2 = analise.get("tco2_estimado")
    biomassa = analise.get("biomassa_tha")
    elegibilidade = analise.get("elegibilidade", "—")
    cor_eleg = _cor_elegibilidade(elegibilidade)
    label_eleg = _label_elegibilidade(elegibilidade)

    score_adic = analise.get("score_adicionalidade", 0)
    score_perm = analise.get("score_permanencia", 0)
    score_titu = analise.get("score_titularidade", 0)
    score_tam  = analise.get("score_tamanho", 0)
    score_total = round(
        (float(score_adic or 0) + float(score_perm or 0)
         + float(score_titu or 0) + float(score_tam or 0)) / 4, 1
    )

    nome_propriedade = prop.get("nome_propriedade", "—")
    bioma = prop.get("bioma", "—")
    tipo_veg = prop.get("tipo_vegetacao", "—")
    area_total = prop.get("area_total_ha")
    area_veg = prop.get("area_vegetacao_ha")
    idade = prop.get("idade_vegetacao_anos", "—")
    codigo_car = prop.get("codigo_car") or "Não informado"
    nome_usuario = usuario.get("nome", "—")
    email_usuario = usuario.get("email", "—")

    metodo = analise.get("metodo_calculo", "—")
    versao = analise.get("versao_algoritmo", "—")
    camada = analise.get("camada", "—")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<title>Relatório de Carbono — {analise_id_curto}</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @bottom-center {{
      content: "Carbono em Pé — Meridiano Tecnologia  ·  Página " counter(page) " de " counter(pages);
      font-size: 8pt;
      color: #6b7280;
    }}
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    color: {_COR_TEXTO};
    line-height: 1.5;
  }}

  /* ── Cabeçalho ── */
  .cabecalho {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 12px;
    border-bottom: 3px solid {_COR_VERDE_ESCURO};
    margin-bottom: 18px;
  }}
  .cabecalho-marca {{ display: flex; flex-direction: column; gap: 2px; }}
  .marca-titulo {{
    font-size: 17pt;
    font-weight: 700;
    color: {_COR_VERDE_ESCURO};
    letter-spacing: -0.3px;
  }}
  .marca-subtitulo {{
    font-size: 9pt;
    color: {_COR_VERDE_MEDIO};
    font-weight: 500;
  }}
  .cabecalho-meta {{
    text-align: right;
    font-size: 8.5pt;
    color: #4b5563;
    line-height: 1.6;
  }}
  .cabecalho-meta strong {{ color: {_COR_VERDE_ESCURO}; }}

  /* ── Seções ── */
  .secao {{
    margin-bottom: 20px;
  }}
  .secao-titulo {{
    font-size: 11pt;
    font-weight: 700;
    color: {_COR_VERDE_ESCURO};
    border-left: 4px solid {_COR_VERDE_MEDIO};
    padding-left: 8px;
    margin-bottom: 10px;
  }}

  /* ── Grade de dados ── */
  .grade {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 24px;
  }}
  .grade-item {{ display: flex; flex-direction: column; gap: 1px; }}
  .grade-label {{
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #6b7280;
    font-weight: 600;
  }}
  .grade-valor {{
    font-size: 10pt;
    color: {_COR_TEXTO};
    font-weight: 500;
  }}

  /* ── Destaque tCO₂ ── */
  .destaque-tco2 {{
    background: {_COR_VERDE_CLARO};
    border: 1.5px solid {_COR_BORDA};
    border-radius: 6px;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }}
  .tco2-bloco {{ display: flex; flex-direction: column; gap: 2px; }}
  .tco2-label {{
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #4b5563;
    font-weight: 600;
  }}
  .tco2-valor {{
    font-size: 26pt;
    font-weight: 800;
    color: {_COR_VERDE_ESCURO};
    line-height: 1.1;
  }}
  .tco2-unidade {{
    font-size: 11pt;
    font-weight: 500;
    color: {_COR_VERDE_MEDIO};
  }}
  .tco2-biomassa {{
    font-size: 8.5pt;
    color: #4b5563;
    margin-top: 2px;
  }}
  .eleg-bloco {{
    text-align: right;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }}
  .eleg-label {{
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #4b5563;
    font-weight: 600;
  }}
  .eleg-badge {{
    font-size: 14pt;
    font-weight: 800;
    color: {cor_eleg};
  }}
  .eleg-total {{
    font-size: 9pt;
    color: #6b7280;
  }}

  /* ── Barras de pontuação ── */
  .dimensao {{
    margin-bottom: 10px;
  }}
  .dimensao-cabecalho {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 3px;
  }}
  .dimensao-nome {{
    font-size: 9.5pt;
    font-weight: 700;
    color: {_COR_VERDE_ESCURO};
  }}
  .barra-container {{
    width: 100%;
    height: 10px;
    background: #e5e7eb;
    border-radius: 5px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
  }}
  .barra-preenchida {{
    height: 100%;
    border-radius: 5px;
  }}
  .barra-valor {{
    font-size: 8.5pt;
    color: #4b5563;
    margin-left: 8px;
    white-space: nowrap;
  }}
  .dimensao-descricao {{
    font-size: 7.5pt;
    color: #6b7280;
    margin-top: 3px;
    font-style: italic;
  }}

  /* ── Notas metodológicas ── */
  .nota-box {{
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    padding: 11px 14px;
    font-size: 8.5pt;
    color: #374151;
    line-height: 1.55;
    margin-bottom: 14px;
  }}
  .nota-box strong {{ color: {_COR_VERDE_ESCURO}; }}

  /* ── Disclaimer ── */
  .disclaimer {{
    background: #fff7ed;
    border: 1.5px solid #fdba74;
    border-radius: 5px;
    padding: 10px 14px;
    font-size: 8pt;
    color: #92400e;
    line-height: 1.5;
  }}
  .disclaimer strong {{ color: #78350f; }}

  /* ── Rodapé ── */
  .rodape {{
    margin-top: 22px;
    padding-top: 10px;
    border-top: 1.5px solid {_COR_BORDA};
    font-size: 7.5pt;
    color: #6b7280;
  }}
  .rodape-titulo {{ font-weight: 700; color: {_COR_VERDE_ESCURO}; margin-bottom: 4px; }}
  .rodape-links {{ display: flex; flex-direction: column; gap: 2px; }}
  .rodape-link {{ color: #2563eb; }}

  /* ── Quebra de página ── */
  .quebra {{ page-break-before: always; }}
</style>
</head>
<body>

<!-- ════════════════════════════════════════════════════════
     CABEÇALHO
════════════════════════════════════════════════════════ -->
<div class="cabecalho">
  <div class="cabecalho-marca">
    <div class="marca-titulo">Carbono em Pé</div>
    <div class="marca-subtitulo">Meridiano Tecnologia</div>
  </div>
  <div class="cabecalho-meta">
    <strong>Relatório de Diagnóstico de Carbono</strong><br/>
    Emitido em: {data_geracao}<br/>
    Código: <strong>{analise_id_curto}</strong> &nbsp;·&nbsp; Camada {camada}
  </div>
</div>


<!-- ════════════════════════════════════════════════════════
     DADOS DA PROPRIEDADE E DO RESPONSÁVEL
════════════════════════════════════════════════════════ -->
<div class="secao">
  <div class="secao-titulo">Dados da Propriedade</div>
  <div class="grade">
    <div class="grade-item">
      <span class="grade-label">Nome da propriedade</span>
      <span class="grade-valor">{nome_propriedade}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Responsável</span>
      <span class="grade-valor">{nome_usuario}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Bioma</span>
      <span class="grade-valor">{bioma}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Tipo de vegetação</span>
      <span class="grade-valor">{tipo_veg}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Área total da propriedade</span>
      <span class="grade-valor">{_formatar_numero(area_total, 2, "ha")}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Área de vegetação nativa</span>
      <span class="grade-valor">{_formatar_numero(area_veg, 2, "ha")}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Idade estimada da vegetação</span>
      <span class="grade-valor">{idade} anos</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Código CAR</span>
      <span class="grade-valor">{codigo_car}</span>
    </div>
    <div class="grade-item">
      <span class="grade-label">Contato</span>
      <span class="grade-valor">{email_usuario}</span>
    </div>
  </div>
</div>


<!-- ════════════════════════════════════════════════════════
     RESULTADO — tCO₂
════════════════════════════════════════════════════════ -->
<div class="secao">
  <div class="secao-titulo">Resultado do Cálculo de Estoque de Carbono</div>
  <div class="destaque-tco2">
    <div class="tco2-bloco">
      <span class="tco2-label">Estoque estimado de CO₂ equivalente</span>
      <span class="tco2-valor">{_formatar_numero(tco2, 1)}</span>
      <span class="tco2-unidade">toneladas de CO₂ equivalente (tCO₂e)</span>
      <span class="tco2-biomassa">Biomassa total: {_formatar_numero(biomassa, 2, "Mg/ha")}</span>
    </div>
    <div class="eleg-bloco">
      <span class="eleg-label">Elegibilidade estimada</span>
      <span class="eleg-badge">{label_eleg}</span>
      <span class="eleg-total">Pontuação geral: {score_total:.0f} / 100</span>
    </div>
  </div>
</div>


<!-- ════════════════════════════════════════════════════════
     PONTUAÇÃO DE ELEGIBILIDADE
════════════════════════════════════════════════════════ -->
<div class="secao">
  <div class="secao-titulo">Pontuação de Elegibilidade para Mercado Voluntário de Carbono</div>

  <div class="dimensao">
    <div class="dimensao-cabecalho">
      <span class="dimensao-nome">Adicionalidade</span>
    </div>
    {_barra_pontuacao(score_adic)}
    <div class="dimensao-descricao">
      Avalia se a conservação excede as obrigações legais e gera benefício climático real e verificável.
    </div>
  </div>

  <div class="dimensao">
    <div class="dimensao-cabecalho">
      <span class="dimensao-nome">Permanência</span>
    </div>
    {_barra_pontuacao(score_perm)}
    <div class="dimensao-descricao">
      Avalia o risco de reversão do estoque de carbono ao longo do tempo, considerando pressão histórica de desmatamento e maturidade da vegetação.
    </div>
  </div>

  <div class="dimensao">
    <div class="dimensao-cabecalho">
      <span class="dimensao-nome">Titularidade e Conformidade</span>
    </div>
    {_barra_pontuacao(score_titu)}
    <div class="dimensao-descricao">
      Avalia a regularidade fundiária e ambiental: Reserva Legal averbada e Áreas de Preservação Permanente registradas no CAR.
    </div>
  </div>

  <div class="dimensao">
    <div class="dimensao-cabecalho">
      <span class="dimensao-nome">Tamanho e Viabilidade Econômica</span>
    </div>
    {_barra_pontuacao(score_tam)}
    <div class="dimensao-descricao">
      Projetos acima de 500 ha apresentam maior viabilidade de transação e atração de compradores institucionais no mercado voluntário.
    </div>
  </div>
</div>


<!-- ════════════════════════════════════════════════════════
     NOTA METODOLÓGICA
════════════════════════════════════════════════════════ -->
<div class="secao">
  <div class="secao-titulo">Nota Metodológica</div>
  <div class="nota-box">
    <strong>Metodologia de cálculo de biomassa:</strong> O estoque de carbono foi estimado por meio de equações alométricas regionais de
    <strong>Chave et al. (2005)</strong> — <em>Global Ecology and Biogeography</em>, 14:677–688 — calibradas para zonas climáticas
    tropicais e subtropicais do Brasil. Os coeficientes foram aplicados com diâmetro à altura do peito (DAP) médio representativo
    por bioma e tipo de vegetação, e escalonados pela densidade arbórea típica. A biomassa subterrânea foi estimada com fatores
    raiz/parte aérea do <strong>IPCC (2006 Guidelines for National Greenhouse Gas Inventories, Tabela 4.4)</strong>.
    O fator de conversão biomassa → carbono utilizado foi <strong>0,47</strong> (padrão IPCC) e a conversão para CO₂ equivalente
    aplicou o fator <strong>44/12</strong>.<br/><br/>
    <strong>Pontuação de elegibilidade:</strong> Os critérios utilizados são compatíveis com os princípios dos padrões
    <strong>Verra VCS (Verified Carbon Standard)</strong> e <strong>REDD+ (Reducing Emissions from Deforestation and Forest
    Degradation)</strong>. As quatro dimensões avaliadas — adicionalidade, permanência, titularidade e tamanho — são os pilares
    exigidos por mercados voluntários de carbono de alta integridade.<br/><br/>
    Método registrado: <strong>{metodo}</strong> · Versão do algoritmo: <strong>{versao}</strong>
  </div>
</div>


<!-- ════════════════════════════════════════════════════════
     DISCLAIMER
════════════════════════════════════════════════════════ -->
<div class="disclaimer">
  <strong>&#9888; Aviso importante:</strong> Este documento é um <strong>diagnóstico preliminar automatizado</strong> e
  <strong>não constitui laudo técnico, parecer pericial ou certificação de crédito de carbono</strong>.
  Os valores de tCO₂e são estimativas baseadas em parâmetros médios regionais e não substituem inventário
  florestal de campo, auditoria por organismo de validação/verificação (VVB) acreditado, nem processo formal
  de certificação pelos padrões Verra VCS, Gold Standard ou equivalente.
  A Meridiano Tecnologia não assume responsabilidade por decisões comerciais, legais ou ambientais tomadas
  com base exclusiva neste relatório. Consulte um engenheiro florestal habilitado antes de iniciar qualquer
  projeto de mercado voluntário de carbono.
</div>


<!-- ════════════════════════════════════════════════════════
     RODAPÉ — FONTES OFICIAIS
════════════════════════════════════════════════════════ -->
<div class="rodape">
  <div class="rodape-titulo">Fontes e Referências Oficiais</div>
  <div class="rodape-links">
    <span>· IPCC (2006). <em>2006 IPCC Guidelines for National Greenhouse Gas Inventories</em>.
      <span class="rodape-link">https://www.ipcc-nggip.iges.or.jp/public/2006gl/</span></span>
    <span>· Chave et al. (2005). <em>Tree allometry and improved estimation of carbon stocks...</em>
      Global Ecology and Biogeography, 14(6):677–688.</span>
    <span>· Verra VCS Standard.
      <span class="rodape-link">https://verra.org/programs/verified-carbon-standard/</span></span>
    <span>· REDD+ (ONU-REDD).
      <span class="rodape-link">https://www.unredd.net/</span></span>
    <span>· Sistema Nacional de Cadastro Ambiental Rural (SICAR).
      <span class="rodape-link">https://www.car.gov.br/</span></span>
  </div>
</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Conversão HTML → PDF
# ---------------------------------------------------------------------------

def _converter_para_pdf(html: str) -> bytes:
    buffer = io.BytesIO()
    WeasyHTML(string=html).write_pdf(buffer)
    return buffer.getvalue()
