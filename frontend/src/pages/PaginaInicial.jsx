import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Corrige ícones do Leaflet com Vite
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

// ─── Paleta ──────────────────────────────────────────────────────────────────

const C = {
  fundoEscuro:  '#0d1f0f',
  fundoSecao:   '#0f2312',
  fundoCard:    '#132a16',
  fundoRodape:  '#0a1a0c',
  borda:        '#1e4024',
  bordaInput:   '#234527',
  inputBg:      '#1a3320',
  verde:        '#4caf72',
  verdeClaro:   '#6fcf97',
  textoClaro:   '#e8f5ed',
  textoMuted:   '#86a98c',
}

// ─── Dados estáticos ─────────────────────────────────────────────────────────

const BIOMAS = [
  'Amazônia',
  'Cerrado',
  'Mata Atlântica',
  'Caatinga',
  'Pampa',
  'Pantanal',
]

const VEGETACOES_POR_BIOMA = {
  'Amazônia':       ['Floresta primária', 'Floresta secundária', 'Savana arborizada'],
  'Cerrado':        ['Floresta primária', 'Floresta secundária', 'Savana arborizada', 'Campo cerrado'],
  'Mata Atlântica': ['Floresta primária', 'Floresta secundária', 'Restinga', 'Manguezal'],
  'Caatinga':       ['Savana arborizada', 'Campo cerrado'],
  'Pampa':          ['Campo cerrado'],
  'Pantanal':       ['Savana arborizada', 'Manguezal'],
}

// Fatores de biomassa em tMS/ha — IPCC 2006 Guidelines, Tabela 4.7
const FATORES_BIOMASSA = {
  'Amazônia': {
    'Floresta primária':   310,
    'Floresta secundária': 168,
    'Savana arborizada':    92,
  },
  'Cerrado': {
    'Floresta primária':   145,
    'Floresta secundária':  98,
    'Savana arborizada':    72,
    'Campo cerrado':        38,
  },
  'Mata Atlântica': {
    'Floresta primária':   260,
    'Floresta secundária': 140,
    'Restinga':             72,
    'Manguezal':            88,
  },
  'Caatinga': {
    'Savana arborizada':   55,
    'Campo cerrado':       28,
  },
  'Pampa': {
    'Campo cerrado':       22,
  },
  'Pantanal': {
    'Savana arborizada':   78,
    'Manguezal':           85,
  },
}

// Pontuação base de adicionalidade por bioma (pressão de desmatamento histórica)
const ADICIONALIDADE_BIOMA = {
  'Amazônia':       85,
  'Mata Atlântica': 80,
  'Cerrado':        70,
  'Pantanal':       65,
  'Caatinga':       55,
  'Pampa':          40,
}

const CAMADAS = [
  {
    num: '1',
    titulo: 'Estimativa IPCC',
    preco: 'Gratuita',
    descricao: 'Cálculo imediato de tCO₂ com fatores IPCC nível 1. Sem cadastro necessário.',
    cta: 'Calcular agora',
    ancora: '#estimativa',
    destaque: true,
  },
  {
    num: '2',
    titulo: 'Alometria Regional',
    preco: 'R$ 19',
    descricao: 'Equações alométricas de Chave et al. 2005 por bioma, espécie e DAP médio.',
    cta: 'Cadastre-se',
    rota: '/cadastro',
    destaque: false,
  },
  {
    num: '3',
    titulo: 'Análise por Área',
    preco: 'R$ 19 – 129',
    descricao: 'Análise detalhada com elegibilidade completa por faixa de área.',
    cta: 'Cadastre-se',
    rota: '/cadastro',
    destaque: false,
  },
  {
    num: '4',
    titulo: 'Projeto Completo',
    preco: 'Sob consulta',
    descricao: 'Estruturação de projeto de créditos de carbono para o mercado voluntário.',
    cta: 'Fale conosco',
    email: 'contato@meridianotecnologia.com.br',
    destaque: false,
  },
]

const CARDS_CONHECA = [
  {
    icone: '🌿',
    titulo: 'O que são créditos de carbono?',
    texto:
      'Créditos de carbono são certificados que representam a redução ou remoção de uma tonelada de CO₂ da atmosfera. Propriedades rurais com vegetação nativa conservada podem gerar e vender esses créditos no mercado voluntário.',
  },
  {
    icone: '✅',
    titulo: 'Como funciona a verificação?',
    texto:
      'A verificação é realizada por auditores independentes (VVB) credenciados por padrões como Verra VCS ou Gold Standard. Eles confirmam que o carbono foi de fato removido ou evitado antes de qualquer emissão de créditos.',
  },
  {
    icone: '📐',
    titulo: 'Metodologia IPCC e Verra',
    texto:
      'Usamos os Guidelines IPCC 2006 para estimativas de biomassa e os critérios do Verified Carbon Standard (Verra) para avaliar adicionalidade, permanência e titularidade fundiária do projeto.',
  },
  {
    icone: '🇧🇷',
    titulo: 'Mercado voluntário no Brasil',
    texto:
      'O Brasil possui o maior potencial de geração de créditos de carbono do mundo, com mais de 60 milhões de hectares de vegetação nativa em propriedades privadas passíveis de certificação.',
  },
]

const FONTES_OFICIAIS = [
  { nome: 'IPCC 2006 Guidelines', url: 'https://www.ipcc-nggip.iges.or.jp/public/2006gl/' },
  { nome: 'Verra VCS Standard',   url: 'https://verra.org/programs/verified-carbon-standard/' },
  { nome: 'ONU-REDD',             url: 'https://www.unredd.net/' },
  { nome: 'SICAR — CAR',          url: 'https://www.car.gov.br/' },
  { nome: 'MapBiomas — INPE',     url: 'https://mapbiomas.org/' },
]

// ─── Funções de cálculo ───────────────────────────────────────────────────────

function calcularTCO2(areaHa, fatorTMSha) {
  // Fórmula IPCC Nível 1: biomassa × fator_carbono × fator_CO₂
  return areaHa * fatorTMSha * 0.47 * (44 / 12)
}

function calcularElegibilidade(bioma, areaHa, idadeAnos) {
  const adicionalidade = Math.min(
    100,
    (ADICIONALIDADE_BIOMA[bioma] ?? 60) + (areaHa > 200 ? 8 : 0)
  )
  const permanencia  = Math.min(95, 30 + idadeAnos * 1.2)
  const titularidade = 50 // requer dados de CAR — fixo na estimativa gratuita
  const tamanho =
    areaHa < 50 ? 15 : areaHa < 200 ? 40 : areaHa < 500 ? 68 : 90
  const total = (adicionalidade + permanencia + titularidade + tamanho) / 4
  const classificacao =
    total >= 70 ? 'Alto' : total >= 40 ? 'Médio' : 'Baixo'
  return { adicionalidade, permanencia, titularidade, tamanho, total, classificacao }
}

function parsearCoordenadas(texto) {
  const m = texto.trim().match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/)
  if (!m) return null
  const lat = parseFloat(m[1])
  const lon = parseFloat(m[2])
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null
  return [lat, lon]
}

function formatarTCO2(valor) {
  if (valor >= 1_000_000)
    return `${(valor / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} M`
  if (valor >= 1_000)
    return `${(valor / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`
  return valor.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

// ─── Subcomponentes ───────────────────────────────────────────────────────────

function AtualizarVistaMapa({ posicao }) {
  const mapa = useMap()
  useEffect(() => {
    if (posicao) mapa.setView(posicao, 12, { animate: true })
  }, [posicao, mapa])
  return null
}

function BarraElegibilidade({ rotulo, valor }) {
  const pct = Math.min(100, Math.max(0, valor))
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: C.textoMuted }}>{rotulo}</span>
        <span className="font-semibold" style={{ color: C.verde }}>
          {Math.round(pct)} / 100
        </span>
      </div>
      <div className="h-1.5 rounded-full" style={{ background: '#1a3320' }}>
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: C.verde }}
        />
      </div>
    </div>
  )
}

function BadgeCamada({ texto, destaque }) {
  return (
    <span
      className="text-xs font-bold px-2 py-0.5 rounded-full"
      style={{
        background: destaque ? 'rgba(255,255,255,0.2)' : C.inputBg,
        color: destaque ? '#fff' : C.verde,
      }}
    >
      {texto}
    </span>
  )
}

function SelectEstilo({ value, onChange, disabled, children }) {
  return (
    <select
      value={value}
      onChange={onChange}
      disabled={disabled}
      className="w-full rounded-xl px-4 py-3 text-sm outline-none appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        background: C.inputBg,
        color: value ? C.textoClaro : C.textoMuted,
        border: `1px solid ${C.bordaInput}`,
      }}
    >
      {children}
    </select>
  )
}

function SliderEstilo({ min, max, value, onChange, rotulo, unidade }) {
  return (
    <div className="mb-5">
      <div className="flex justify-between items-center mb-2">
        <label className="text-sm font-semibold" style={{ color: C.textoClaro }}>
          {rotulo}
        </label>
        <span className="text-sm font-bold tabular-nums" style={{ color: C.verde }}>
          {value} {unidade}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={onChange}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{ accentColor: C.verde, background: C.inputBg }}
      />
      <div className="flex justify-between text-xs mt-1" style={{ color: C.textoMuted }}>
        <span>{min} {unidade}</span>
        <span>{max} {unidade}</span>
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function PaginaInicial() {
  const navegar = useNavigate()

  // Estado do formulário
  const [bioma, setBioma]           = useState('')
  const [vegetacao, setVegetacao]   = useState('')
  const [area, setArea]             = useState(100)
  const [idade, setIdade]           = useState(30)
  const [coordTexto, setCoordTexto] = useState('')
  const [posicao, setPosicao]       = useState(null)

  // Reseta vegetação quando bioma muda
  useEffect(() => { setVegetacao('') }, [bioma])

  // Parse de coordenadas em tempo real
  useEffect(() => {
    setPosicao(parsearCoordenadas(coordTexto))
  }, [coordTexto])

  const vegetacoesDisponiveis = bioma ? (VEGETACOES_POR_BIOMA[bioma] ?? []) : []
  const fator = (bioma && vegetacao)
    ? (FATORES_BIOMASSA[bioma]?.[vegetacao] ?? 72)
    : 72

  const tco2 = useMemo(
    () => calcularTCO2(area, fator),
    [area, fator]
  )

  const eleg = useMemo(
    () => calcularElegibilidade(bioma || 'Cerrado', area, idade),
    [bioma, area, idade]
  )

  const corClassificacao =
    eleg.classificacao === 'Alto'  ? '#4caf72' :
    eleg.classificacao === 'Médio' ? '#f59e0b' : '#ef4444'

  const irPara = (rota) => (e) => { e.preventDefault(); navegar(rota) }

  return (
    <div
      className="min-h-screen"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro, color: C.textoClaro }}
    >

      {/* ════════════════════════════════════
          NAVBAR
      ════════════════════════════════════ */}
      <nav
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 py-4"
        style={{
          background: 'rgba(13,31,15,0.92)',
          backdropFilter: 'blur(10px)',
          borderBottom: `1px solid ${C.borda}`,
        }}
      >
        <a
          href="#hero"
          className="text-lg font-bold tracking-tight"
          style={{ color: C.verde, textDecoration: 'none' }}
        >
          🌱 Carbono em Pé
        </a>

        <div className="flex items-center gap-5">
          <a
            href="#camadas"
            className="text-sm font-medium hidden sm:block transition-colors hover:opacity-80"
            style={{ color: C.textoMuted, textDecoration: 'none' }}
          >
            Camadas
          </a>
          <a
            href="#conheca"
            className="text-sm font-medium hidden sm:block transition-colors hover:opacity-80"
            style={{ color: C.textoMuted, textDecoration: 'none' }}
          >
            Sobre
          </a>
          <Link
            to="/login"
            className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90 active:scale-95"
            style={{ background: C.verde, color: '#fff', textDecoration: 'none' }}
          >
            Entrar →
          </Link>
        </div>
      </nav>

      {/* ════════════════════════════════════
          HERO
      ════════════════════════════════════ */}
      <section
        id="hero"
        className="flex flex-col items-center justify-center text-center px-4 pt-36 pb-20"
        style={{
          background: `linear-gradient(180deg, #091508 0%, ${C.fundoEscuro} 100%)`,
          minHeight: '100vh',
        }}
      >
        <span
          className="inline-block text-xs font-semibold uppercase tracking-widest px-4 py-1.5 rounded-full mb-6"
          style={{ background: C.fundoCard, color: C.verde, border: `1px solid ${C.borda}` }}
        >
          Plataforma de diagnóstico de carbono
        </span>

        <h1
          className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-5 max-w-3xl"
          style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
        >
          Descubra o valor climático{' '}
          <span style={{ color: C.verde }}>da sua terra</span>
        </h1>

        <p
          className="text-base sm:text-lg max-w-xl mb-14 leading-relaxed"
          style={{ color: C.textoMuted }}
        >
          Diagnóstico de estoque de carbono com metodologia IPCC e elegibilidade
          para o mercado voluntário de créditos de carbono.
        </p>

        {/* Quatro camadas */}
        <div
          id="camadas"
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full max-w-5xl"
        >
          {CAMADAS.map((c) => {
            const href =
              c.ancora ? c.ancora :
              c.email  ? `mailto:${c.email}` :
              c.rota   ? c.rota : '#'

            const onClick =
              c.rota ? irPara(c.rota) :
              c.ancora ? undefined : undefined

            return (
              <a
                key={c.num}
                href={href}
                onClick={onClick}
                className="flex flex-col text-left p-5 rounded-2xl transition-all duration-200 hover:scale-[1.03] hover:shadow-lg"
                style={{
                  background: c.destaque ? C.verde : C.fundoCard,
                  border: `1.5px solid ${c.destaque ? C.verde : C.borda}`,
                  color: c.destaque ? '#fff' : C.textoClaro,
                  textDecoration: 'none',
                  cursor: 'pointer',
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <BadgeCamada texto={`Camada ${c.num}`} destaque={c.destaque} />
                  <span
                    className="text-xs font-semibold"
                    style={{ color: c.destaque ? 'rgba(255,255,255,0.9)' : C.verde }}
                  >
                    {c.preco}
                  </span>
                </div>
                <h3 className="font-bold text-base mb-2">{c.titulo}</h3>
                <p
                  className="text-sm leading-relaxed mb-4 flex-1"
                  style={{ color: c.destaque ? 'rgba(255,255,255,0.78)' : C.textoMuted }}
                >
                  {c.descricao}
                </p>
                <span
                  className="text-sm font-semibold"
                  style={{ color: c.destaque ? '#fff' : C.verde }}
                >
                  {c.cta} →
                </span>
              </a>
            )
          })}
        </div>
      </section>

      {/* ════════════════════════════════════
          FORMULÁRIO DE ESTIMATIVA
      ════════════════════════════════════ */}
      <section id="estimativa" className="py-20 px-4" style={{ background: C.fundoSecao }}>
        <div className="max-w-5xl mx-auto">

          {/* Cabeçalho da seção */}
          <div className="text-center mb-12">
            <span
              className="inline-block text-xs font-semibold uppercase tracking-widest px-4 py-1.5 rounded-full mb-4"
              style={{ background: C.fundoCard, color: C.verde, border: `1px solid ${C.borda}` }}
            >
              Camada 1 · Gratuita
            </span>
            <h2
              className="text-3xl sm:text-4xl font-bold mb-3"
              style={{ color: C.textoClaro, letterSpacing: '-0.01em' }}
            >
              Estimativa gratuita de tCO₂
            </h2>
            <p className="text-sm" style={{ color: C.textoMuted }}>
              Preencha os dados da propriedade e veja o resultado calculado em tempo real.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* ── Formulário ── */}
            <div
              className="rounded-2xl p-6"
              style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
            >
              {/* Bioma */}
              <div className="mb-5">
                <label className="block text-sm font-semibold mb-2" style={{ color: C.textoClaro }}>
                  Bioma
                </label>
                <SelectEstilo value={bioma} onChange={(e) => setBioma(e.target.value)}>
                  <option value="" style={{ color: C.textoMuted }}>Selecione o bioma</option>
                  {BIOMAS.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </SelectEstilo>
              </div>

              {/* Tipo de vegetação */}
              <div className="mb-5">
                <label className="block text-sm font-semibold mb-2" style={{ color: C.textoClaro }}>
                  Tipo de vegetação
                </label>
                <SelectEstilo
                  value={vegetacao}
                  onChange={(e) => setVegetacao(e.target.value)}
                  disabled={!bioma}
                >
                  <option value="">
                    {bioma ? 'Selecione o tipo de vegetação' : 'Selecione o bioma primeiro'}
                  </option>
                  {vegetacoesDisponiveis.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </SelectEstilo>
              </div>

              {/* Área */}
              <SliderEstilo
                rotulo="Área de vegetação nativa"
                unidade="ha"
                min={1}
                max={500}
                value={area}
                onChange={(e) => setArea(Number(e.target.value))}
              />

              {/* Idade */}
              <SliderEstilo
                rotulo="Idade da vegetação"
                unidade="anos"
                min={5}
                max={80}
                value={idade}
                onChange={(e) => setIdade(Number(e.target.value))}
              />

              {/* Localização */}
              <div>
                <label className="block text-sm font-semibold mb-1" style={{ color: C.textoClaro }}>
                  Localização{' '}
                  <span className="font-normal" style={{ color: C.textoMuted }}>(opcional)</span>
                </label>
                <input
                  type="text"
                  placeholder="Ex: -3.4653, -62.2159"
                  className="w-full rounded-xl px-4 py-3 text-sm outline-none"
                  style={{
                    background: C.inputBg,
                    color: C.textoClaro,
                    border: `1px solid ${C.bordaInput}`,
                  }}
                  value={coordTexto}
                  onChange={(e) => setCoordTexto(e.target.value)}
                />
                <p className="text-xs mt-1.5" style={{ color: C.textoMuted }}>
                  Coordenadas no formato latitude, longitude — ex: -3.4653, -62.2159
                </p>
              </div>
            </div>

            {/* ── Resultado + Mapa ── */}
            <div className="flex flex-col gap-4">

              {/* Resultado tCO₂ + elegibilidade */}
              <div
                className="rounded-2xl p-6 flex-1"
                style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
              >
                <p
                  className="text-xs uppercase tracking-widest font-semibold mb-1"
                  style={{ color: C.textoMuted }}
                >
                  Estoque estimado · IPCC Nível 1
                </p>

                <div className="flex items-end gap-2 mb-1">
                  <span
                    className="font-bold leading-none"
                    style={{ fontSize: '3rem', color: C.verde }}
                  >
                    {formatarTCO2(tco2)}
                  </span>
                  <span className="text-lg mb-1" style={{ color: C.textoMuted }}>
                    tCO₂e
                  </span>
                </div>

                <p className="text-xs mb-5" style={{ color: C.textoMuted }}>
                  {area} ha × {fator} tMS/ha × 0,47 × 44/12
                  {bioma && vegetacao ? '' : ' · fator padrão 72 tMS/ha'}
                </p>

                {/* Classificação de elegibilidade */}
                <div
                  className="flex items-center justify-between px-4 py-3 rounded-xl mb-5"
                  style={{ background: C.inputBg }}
                >
                  <div>
                    <p className="text-xs font-semibold" style={{ color: C.textoMuted }}>
                      Elegibilidade estimada
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: C.textoMuted }}>
                      Camada 1 · resultado simplificado
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-base" style={{ color: corClassificacao }}>
                      {eleg.classificacao}
                    </p>
                    <p className="text-xs" style={{ color: C.textoMuted }}>
                      {Math.round(eleg.total)} / 100
                    </p>
                  </div>
                </div>

                <BarraElegibilidade rotulo="Adicionalidade" valor={eleg.adicionalidade} />
                <BarraElegibilidade rotulo="Permanência" valor={eleg.permanencia} />
                <BarraElegibilidade
                  rotulo="Titularidade (requer CAR)"
                  valor={eleg.titularidade}
                />
                <BarraElegibilidade rotulo="Tamanho e viabilidade" valor={eleg.tamanho} />

                <button
                  onClick={() => navegar('/cadastro')}
                  className="w-full mt-5 py-3 rounded-xl font-semibold text-sm transition-all hover:opacity-90 active:scale-[0.98]"
                  style={{ background: C.verde, color: '#fff' }}
                >
                  Análise detalhada — Camada 2 →
                </button>
                <p className="text-xs text-center mt-2" style={{ color: C.textoMuted }}>
                  Cadastro gratuito · Análise alométrica por R$ 19
                </p>
              </div>

              {/* Mapa Leaflet */}
              {posicao ? (
                <div
                  className="rounded-2xl overflow-hidden flex-shrink-0"
                  style={{ height: '200px', border: `1px solid ${C.borda}` }}
                >
                  <MapContainer
                    center={posicao}
                    zoom={12}
                    style={{ height: '100%', width: '100%' }}
                    zoomControl={true}
                    scrollWheelZoom={false}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={posicao}>
                      <Popup>
                        {bioma && vegetacao
                          ? `${bioma} · ${vegetacao}`
                          : 'Localização informada'}
                        <br />
                        <small>{posicao[0].toFixed(4)}, {posicao[1].toFixed(4)}</small>
                      </Popup>
                    </Marker>
                    <AtualizarVistaMapa posicao={posicao} />
                  </MapContainer>
                </div>
              ) : (
                <div
                  className="rounded-2xl flex flex-col items-center justify-center flex-shrink-0"
                  style={{
                    height: '200px',
                    background: C.fundoCard,
                    border: `1.5px dashed ${C.borda}`,
                  }}
                >
                  <span className="text-4xl mb-3">🗺️</span>
                  <p className="text-sm text-center leading-relaxed" style={{ color: C.textoMuted }}>
                    Informe coordenadas acima<br />para ver no mapa
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════
          SEÇÃO CONHEÇA
      ════════════════════════════════════ */}
      <section id="conheca" className="py-20 px-4" style={{ background: C.fundoEscuro }}>
        <div className="max-w-5xl mx-auto">

          <div className="text-center mb-12">
            <h2
              className="text-3xl sm:text-4xl font-bold mb-3"
              style={{ color: C.textoClaro, letterSpacing: '-0.01em' }}
            >
              Conheça o mercado de carbono
            </h2>
            <p className="text-sm" style={{ color: C.textoMuted }}>
              Tudo o que você precisa saber antes de iniciar seu projeto de créditos.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {CARDS_CONHECA.map((card) => (
              <div
                key={card.titulo}
                className="rounded-2xl p-6"
                style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
              >
                <div className="text-4xl mb-4">{card.icone}</div>
                <h3
                  className="font-bold text-base mb-2"
                  style={{ color: C.textoClaro }}
                >
                  {card.titulo}
                </h3>
                <p
                  className="text-sm leading-relaxed"
                  style={{ color: C.textoMuted }}
                >
                  {card.texto}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════
          RODAPÉ — LINKS OFICIAIS
      ════════════════════════════════════ */}
      <footer
        className="py-12 px-4"
        style={{ background: C.fundoRodape, borderTop: `1px solid ${C.borda}` }}
      >
        <div className="max-w-3xl mx-auto text-center">
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-5"
            style={{ color: C.textoMuted }}
          >
            Fontes e referências oficiais
          </p>

          <div className="flex flex-wrap justify-center gap-3 mb-8">
            {FONTES_OFICIAIS.map((f) => (
              <a
                key={f.nome}
                href={f.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-medium px-4 py-2 rounded-lg transition-opacity hover:opacity-75"
                style={{
                  background: C.fundoCard,
                  color: C.verde,
                  border: `1px solid ${C.borda}`,
                  textDecoration: 'none',
                }}
              >
                {f.nome} ↗
              </a>
            ))}
          </div>

          <p className="text-xs mb-1" style={{ color: C.textoMuted }}>
            © {new Date().getFullYear()} Meridiano Tecnologia · Carbono em Pé
          </p>
          <p className="text-xs leading-relaxed" style={{ color: C.textoMuted }}>
            Diagnóstico informativo — não constitui laudo técnico nem certificação de créditos de carbono.
          </p>
        </div>
      </footer>

    </div>
  )
}
