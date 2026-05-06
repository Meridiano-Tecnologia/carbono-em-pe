"""
Carbono em Pé — Gerador de relatório em PDF
Usa ReportLab — sem dependências de sistema externas.
"""
import io
from datetime import date
from loguru import logger
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Flowable,
)
from app.core.database import supabase


# ── Paleta ───────────────────────────────────────────────────────────────────
_VERDE_ESCURO  = colors.HexColor("#1a5c2e")
_VERDE_MEDIO   = colors.HexColor("#2d8c4e")
_VERDE_CLARO   = colors.HexColor("#e8f5ed")
_BORDA         = colors.HexColor("#c8dfd0")
_CINZA_LABEL   = colors.HexColor("#6b7280")
_CINZA_SUBTEXTO = colors.HexColor("#4b5563")
_CINZA_FUNDO   = colors.HexColor("#f9fafb")
_CINZA_BORDA   = colors.HexColor("#e5e7eb")
_LARANJA_BG    = colors.HexColor("#fff7ed")
_LARANJA_BORDA = colors.HexColor("#fdba74")
_LARANJA_TEXTO = colors.HexColor("#92400e")
_TEXTO         = colors.HexColor("#1a1a1a")

_PAGE_W, _PAGE_H = A4
_MARGEM   = 16 * mm
_USABLE_W = _PAGE_W - 2 * _MARGEM


# ── Barra de progresso (Flowable customizado) ─────────────────────────────────
class BarraProgresso(Flowable):
    def __init__(self, pontuacao: float, altura: float = 9):
        super().__init__()
        self.pct    = max(0.0, min(float(pontuacao or 0), 100.0)) / 100
        self._altura = altura

    def wrap(self, availWidth, availHeight):
        self.width  = availWidth
        self.height = self._altura
        return self.width, self.height

    def draw(self):
        self.canv.setFillColor(_CINZA_BORDA)
        self.canv.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        if self.pct > 0:
            self.canv.setFillColor(_VERDE_MEDIO)
            self.canv.rect(0, 0, self.width * self.pct, self.height, fill=1, stroke=0)


# ── Entrada pública ───────────────────────────────────────────────────────────

def gerar_relatorio_pdf(analise_id: str) -> bytes:
    """
    Busca a análise, junta dados da propriedade e do usuário,
    e retorna os bytes do PDF gerado com ReportLab.
    Lança ValueError se a análise não for encontrada.
    """
    dados = _buscar_dados(analise_id)
    return _gerar_pdf_bytes(dados)


# ── Busca de dados ────────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _formatar_numero(valor, casas: int = 2, unidade: str = "") -> str:
    if valor is None:
        return "—"
    try:
        formatado = (
            f"{float(valor):,.{casas}f}"
            .replace(",", "X").replace(".", ",").replace("X", ".")
        )
        return f"{formatado} {unidade}".strip()
    except (TypeError, ValueError):
        return str(valor)


def _cor_elegibilidade(classificacao: str) -> colors.Color:
    return {
        "alto":  colors.HexColor("#1a5c2e"),
        "medio": colors.HexColor("#b45309"),
        "baixo": colors.HexColor("#991b1b"),
    }.get((classificacao or "").lower(), _VERDE_ESCURO)


def _label_elegibilidade(classificacao: str) -> str:
    return {"alto": "Alta", "medio": "Média", "baixo": "Baixa"}.get(
        (classificacao or "").lower(), (classificacao or "").capitalize()
    )


def _rodape_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_CINZA_LABEL)
    canvas.drawCentredString(
        _PAGE_W / 2, 10 * mm,
        f"Carbono em Pé — Meridiano Tecnologia  ·  Página {doc.page}"
    )
    canvas.restoreState()


# ── Estilos ───────────────────────────────────────────────────────────────────

def _estilos() -> dict:
    base = getSampleStyleSheet()

    def novo(nome, **kw):
        return ParagraphStyle(nome, parent=base["Normal"], **kw)

    return {
        "marca_titulo": novo("marca_titulo",
            fontSize=18, fontName="Helvetica-Bold", textColor=_VERDE_ESCURO, leading=22),
        "marca_subtitulo": novo("marca_subtitulo",
            fontSize=9, fontName="Helvetica", textColor=_VERDE_MEDIO),
        "meta_direita": novo("meta_direita",
            fontSize=8.5, textColor=_CINZA_SUBTEXTO, alignment=TA_RIGHT, leading=13),
        "secao_titulo": novo("secao_titulo",
            fontSize=11, fontName="Helvetica-Bold", textColor=_VERDE_ESCURO,
            leading=16, spaceBefore=4, spaceAfter=6),
        "label": novo("label",
            fontSize=7.5, fontName="Helvetica-Bold", textColor=_CINZA_LABEL, leading=11),
        "valor": novo("valor",
            fontSize=10, textColor=_TEXTO, leading=14),
        "tco2_label": novo("tco2_label",
            fontSize=8, fontName="Helvetica-Bold", textColor=_CINZA_SUBTEXTO, leading=11),
        "tco2_valor": novo("tco2_valor",
            fontSize=26, fontName="Helvetica-Bold", textColor=_VERDE_ESCURO, leading=30),
        "tco2_unidade": novo("tco2_unidade",
            fontSize=10, textColor=_VERDE_MEDIO, leading=13),
        "tco2_biomassa": novo("tco2_biomassa",
            fontSize=8.5, textColor=_CINZA_SUBTEXTO, leading=12),
        "eleg_label": novo("eleg_label",
            fontSize=8, fontName="Helvetica-Bold", textColor=_CINZA_SUBTEXTO,
            alignment=TA_RIGHT, leading=11),
        "eleg_total": novo("eleg_total",
            fontSize=9, textColor=_CINZA_LABEL, alignment=TA_RIGHT, leading=12),
        "dimensao_nome": novo("dimensao_nome",
            fontSize=9.5, fontName="Helvetica-Bold", textColor=_VERDE_ESCURO, leading=13),
        "dimensao_score": novo("dimensao_score",
            fontSize=8.5, textColor=_CINZA_SUBTEXTO, alignment=TA_RIGHT, leading=12),
        "dimensao_desc": novo("dimensao_desc",
            fontSize=7.5, fontName="Helvetica-Oblique", textColor=_CINZA_LABEL, leading=11),
        "nota": novo("nota",
            fontSize=8.5, textColor=colors.HexColor("#374151"), leading=13),
        "disclaimer": novo("disclaimer",
            fontSize=8, textColor=_LARANJA_TEXTO, leading=12),
        "fonte_titulo": novo("fonte_titulo",
            fontSize=8, fontName="Helvetica-Bold", textColor=_VERDE_ESCURO, leading=12),
        "fonte": novo("fonte",
            fontSize=7.5, textColor=colors.HexColor("#374151"), leading=11),
    }


# ── Geração do PDF ────────────────────────────────────────────────────────────

def _gerar_pdf_bytes(dados: dict) -> bytes:
    analise  = dados["analise"]
    prop     = dados["propriedade"]
    usuario  = dados["usuario"]
    s        = _estilos()

    data_geracao     = date.today().strftime("%d/%m/%Y")
    analise_id_curto = str(analise.get("id", ""))[:8].upper()
    camada           = analise.get("camada", "—")

    tco2          = analise.get("tco2_estimado")
    biomassa      = analise.get("biomassa_tha")
    elegibilidade = analise.get("elegibilidade") or ""
    cor_eleg      = _cor_elegibilidade(elegibilidade)
    label_eleg    = _label_elegibilidade(elegibilidade)

    score_adic  = float(analise.get("score_adicionalidade") or 0)
    score_perm  = float(analise.get("score_permanencia") or 0)
    score_titu  = float(analise.get("score_titularidade") or 0)
    score_tam   = float(analise.get("score_tamanho") or 0)
    score_total = round((score_adic + score_perm + score_titu + score_tam) / 4, 1)

    nome_propriedade = prop.get("nome_propriedade") or "—"
    bioma            = prop.get("bioma") or "—"
    tipo_veg         = prop.get("tipo_vegetacao") or "—"
    area_total       = prop.get("area_total_ha")
    area_veg         = prop.get("area_vegetacao_ha")
    idade            = prop.get("idade_vegetacao_anos") or "—"
    codigo_car       = prop.get("codigo_car") or "Não informado"
    nome_usuario     = usuario.get("nome") or "—"
    email_usuario    = usuario.get("email") or "—"
    metodo           = analise.get("metodo_calculo") or "—"
    versao           = analise.get("versao_algoritmo") or "—"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_MARGEM,
        rightMargin=_MARGEM,
        topMargin=_MARGEM,
        bottomMargin=18 * mm,
        title=f"Relatório de Carbono — {analise_id_curto}",
        author="Meridiano Tecnologia",
    )

    story = []

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    meta_html = (
        f"<b>Relatório de Diagnóstico de Carbono</b><br/>"
        f"Emitido em: {data_geracao}<br/>"
        f"Código: <b>{analise_id_curto}</b>  ·  Camada {camada}"
    )
    cabecalho = Table(
        [[
            [Paragraph("Carbono em Pé", s["marca_titulo"]),
             Paragraph("Meridiano Tecnologia", s["marca_subtitulo"])],
            Paragraph(meta_html, s["meta_direita"]),
        ]],
        colWidths=[_USABLE_W * 0.55, _USABLE_W * 0.45],
    )
    cabecalho.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(cabecalho)
    story.append(HRFlowable(width="100%", thickness=2, color=_VERDE_ESCURO, spaceAfter=12))

    # ── Dados da Propriedade ───────────────────────────────────────────────────
    story.append(Paragraph("Dados da Propriedade", s["secao_titulo"]))

    def campo(label: str, valor: str) -> list:
        return [Paragraph(label, s["label"]), Paragraph(valor, s["valor"])]

    campos = [
        campo("Nome da propriedade",          nome_propriedade),
        campo("Responsável",                  nome_usuario),
        campo("Bioma",                        bioma),
        campo("Tipo de vegetação",            tipo_veg),
        campo("Área total da propriedade",    _formatar_numero(area_total, 2, "ha")),
        campo("Área de vegetação nativa",     _formatar_numero(area_veg, 2, "ha")),
        campo("Idade estimada da vegetação",  f"{idade} anos"),
        campo("Código CAR",                   codigo_car),
        campo("Contato",                      email_usuario),
    ]
    # Agrupa em pares para duas colunas
    linhas_prop = []
    for i in range(0, len(campos), 2):
        esq = campos[i]
        dir_ = campos[i + 1] if i + 1 < len(campos) else [Paragraph("", s["label"]), Paragraph("", s["valor"])]
        linhas_prop.append([esq, dir_])

    tabela_prop = Table(linhas_prop, colWidths=[_USABLE_W * 0.5, _USABLE_W * 0.5])
    tabela_prop.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabela_prop)
    story.append(Spacer(1, 8))

    # ── Resultado tCO₂ ─────────────────────────────────────────────────────────
    story.append(Paragraph("Resultado do Cálculo de Estoque de Carbono", s["secao_titulo"]))

    eleg_style = ParagraphStyle(
        "eleg_badge", parent=s["eleg_total"],
        fontSize=16, fontName="Helvetica-Bold", textColor=cor_eleg, leading=20,
    )
    caixa_tco2 = Table(
        [[
            [
                Paragraph("Estoque estimado de CO₂ equivalente", s["tco2_label"]),
                Paragraph(_formatar_numero(tco2, 1), s["tco2_valor"]),
                Paragraph("toneladas de CO₂ equivalente (tCO₂e)", s["tco2_unidade"]),
                Paragraph(f"Biomassa total: {_formatar_numero(biomassa, 2, 'Mg/ha')}", s["tco2_biomassa"]),
            ],
            [
                Paragraph("Elegibilidade estimada", s["eleg_label"]),
                Paragraph(label_eleg, eleg_style),
                Paragraph(f"Pontuação geral: {score_total:.0f} / 100", s["eleg_total"]),
            ],
        ]],
        colWidths=[_USABLE_W * 0.6, _USABLE_W * 0.4],
    )
    caixa_tco2.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _VERDE_CLARO),
        ("BOX",           (0, 0), (-1, -1), 1.5, _BORDA),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(caixa_tco2)
    story.append(Spacer(1, 14))

    # ── Pontuação de Elegibilidade ─────────────────────────────────────────────
    story.append(Paragraph(
        "Pontuação de Elegibilidade para Mercado Voluntário de Carbono",
        s["secao_titulo"],
    ))

    dimensoes = [
        (
            "Adicionalidade", score_adic,
            "Avalia se a conservação excede as obrigações legais e gera benefício climático real e verificável.",
        ),
        (
            "Permanência", score_perm,
            "Avalia o risco de reversão do estoque de carbono ao longo do tempo, considerando pressão "
            "histórica de desmatamento e maturidade da vegetação.",
        ),
        (
            "Titularidade e Conformidade", score_titu,
            "Avalia a regularidade fundiária e ambiental: Reserva Legal averbada e Áreas de Preservação "
            "Permanente registradas no CAR.",
        ),
        (
            "Tamanho e Viabilidade Econômica", score_tam,
            "Projetos acima de 500 ha apresentam maior viabilidade de transação e atração de compradores "
            "institucionais no mercado voluntário.",
        ),
    ]
    for nome, score, descricao in dimensoes:
        cabecalho_dim = Table(
            [[Paragraph(nome, s["dimensao_nome"]),
              Paragraph(f"{score:.0f} / 100", s["dimensao_score"])]],
            colWidths=[_USABLE_W * 0.75, _USABLE_W * 0.25],
        )
        cabecalho_dim.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
        ]))
        story.append(cabecalho_dim)
        story.append(BarraProgresso(score))
        story.append(Spacer(1, 3))
        story.append(Paragraph(descricao, s["dimensao_desc"]))
        story.append(Spacer(1, 8))

    # ── Nota Metodológica ──────────────────────────────────────────────────────
    story.append(Paragraph("Nota Metodológica", s["secao_titulo"]))
    nota_texto = (
        "<b>Metodologia de cálculo de biomassa:</b> O estoque de carbono foi estimado por meio de equações "
        "alométricas regionais de <b>Chave et al. (2005)</b> — <i>Global Ecology and Biogeography</i>, "
        "14:677–688 — calibradas para zonas climáticas tropicais e subtropicais do Brasil. Os coeficientes "
        "foram aplicados com diâmetro à altura do peito (DAP) médio representativo por bioma e tipo de "
        "vegetação, e escalonados pela densidade arbórea típica. A biomassa subterrânea foi estimada com "
        "fatores raiz/parte aérea do <b>IPCC (2006 Guidelines for National Greenhouse Gas Inventories, "
        "Tabela 4.4)</b>. O fator de conversão biomassa → carbono utilizado foi <b>0,47</b> (padrão IPCC) "
        "e a conversão para CO₂ equivalente aplicou o fator <b>44/12</b>.<br/><br/>"
        "<b>Pontuação de elegibilidade:</b> Os critérios utilizados são compatíveis com os princípios dos "
        "padrões <b>Verra VCS (Verified Carbon Standard)</b> e <b>REDD+ (Reducing Emissions from "
        "Deforestation and Forest Degradation)</b>. As quatro dimensões avaliadas — adicionalidade, "
        "permanência, titularidade e tamanho — são os pilares exigidos por mercados voluntários de carbono "
        f"de alta integridade.<br/><br/>Método registrado: <b>{metodo}</b> · Versão do algoritmo: <b>{versao}</b>"
    )
    caixa_nota = Table(
        [[Paragraph(nota_texto, s["nota"])]],
        colWidths=[_USABLE_W],
    )
    caixa_nota.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _CINZA_FUNDO),
        ("BOX",           (0, 0), (-1, -1), 1, _CINZA_BORDA),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story.append(caixa_nota)
    story.append(Spacer(1, 12))

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    disclaimer_texto = (
        "<b>Aviso importante:</b> Este documento é um <b>diagnóstico preliminar automatizado</b> e "
        "<b>não constitui laudo técnico, parecer pericial ou certificação de crédito de carbono</b>. "
        "Os valores de tCO₂e são estimativas baseadas em parâmetros médios regionais e não substituem "
        "inventário florestal de campo, auditoria por organismo de validação/verificação (VVB) acreditado, "
        "nem processo formal de certificação pelos padrões Verra VCS, Gold Standard ou equivalente. "
        "A Meridiano Tecnologia não assume responsabilidade por decisões comerciais, legais ou ambientais "
        "tomadas com base exclusiva neste relatório. Consulte um engenheiro florestal habilitado antes de "
        "iniciar qualquer projeto de mercado voluntário de carbono."
    )
    caixa_disc = Table(
        [[Paragraph(disclaimer_texto, s["disclaimer"])]],
        colWidths=[_USABLE_W],
    )
    caixa_disc.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _LARANJA_BG),
        ("BOX",           (0, 0), (-1, -1), 1.5, _LARANJA_BORDA),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(caixa_disc)
    story.append(Spacer(1, 14))

    # ── Fontes e Referências ───────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BORDA, spaceBefore=4, spaceAfter=6))
    story.append(Paragraph("Fontes e Referências Oficiais", s["fonte_titulo"]))
    story.append(Spacer(1, 3))
    for fonte in [
        "· IPCC (2006). <i>2006 IPCC Guidelines for National Greenhouse Gas Inventories</i>. "
        "https://www.ipcc-nggip.iges.or.jp/public/2006gl/",
        "· Chave et al. (2005). <i>Tree allometry and improved estimation of carbon stocks...</i> "
        "Global Ecology and Biogeography, 14(6):677–688.",
        "· Verra VCS Standard. https://verra.org/programs/verified-carbon-standard/",
        "· REDD+ (ONU-REDD). https://www.unredd.net/",
        "· Sistema Nacional de Cadastro Ambiental Rural (SICAR). https://www.car.gov.br/",
    ]:
        story.append(Paragraph(fonte, s["fonte"]))

    doc.build(story, onFirstPage=_rodape_pagina, onLaterPages=_rodape_pagina)
    logger.info(f"PDF gerado com sucesso — analise_id={analise_id_curto}")
    return buffer.getvalue()
