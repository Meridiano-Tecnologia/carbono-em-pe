import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'

// ─── Paleta ───────────────────────────────────────────────────────────────────

const C = {
  fundoEscuro: '#0d1f0f',
  fundoSecao:  '#0f2312',
  fundoCard:   '#132a16',
  borda:       '#1e4024',
  inputBg:     '#1a3320',
  verde:       '#4caf72',
  textoClaro:  '#e8f5ed',
  textoMuted:  '#86a98c',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const COR_ELEGIBILIDADE = {
  alto:  { texto: 'Alto',  cor: '#4caf72', fundo: 'rgba(76,175,114,0.12)'  },
  medio: { texto: 'Médio', cor: '#f59e0b', fundo: 'rgba(245,158,11,0.12)'  },
  baixo: { texto: 'Baixo', cor: '#ef4444', fundo: 'rgba(239,68,68,0.12)'   },
}

function formatarTCO2(v) {
  if (!v && v !== 0) return '—'
  if (v >= 1_000_000) return `${(v / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} M tCO₂e`
  if (v >= 1_000)     return `${(v / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil tCO₂e`
  return `${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} tCO₂e`
}

function formatarData(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return '—'
  }
}

function primeiroNome(nome) {
  return nome?.split(' ')[0] ?? 'usuário'
}

// ─── Subcomponentes ───────────────────────────────────────────────────────────

function Skeleton({ className = '', style = {} }) {
  return (
    <div
      className={`rounded-xl animate-pulse ${className}`}
      style={{ background: C.inputBg, ...style }}
    />
  )
}

function BadgeElegibilidade({ valor }) {
  const conf = COR_ELEGIBILIDADE[valor?.toLowerCase()] ?? COR_ELEGIBILIDADE.baixo
  return (
    <span
      className="text-xs font-semibold px-2.5 py-1 rounded-full"
      style={{ background: conf.fundo, color: conf.cor }}
    >
      {conf.texto}
    </span>
  )
}

function CartaoStat({ rotulo, valor, sub }) {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-1"
      style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
    >
      <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: C.textoMuted }}>
        {rotulo}
      </p>
      <p className="text-2xl font-bold" style={{ color: C.textoClaro }}>
        {valor}
      </p>
      {sub && <p className="text-xs" style={{ color: C.textoMuted }}>{sub}</p>}
    </div>
  )
}

function SkeletonLista() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-2xl p-5"
          style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-2">
              <Skeleton style={{ height: '14px', width: '40%' }} />
              <Skeleton style={{ height: '12px', width: '60%' }} />
            </div>
            <Skeleton style={{ height: '24px', width: '60px', borderRadius: '999px' }} />
          </div>
          <div className="flex gap-4 mt-3">
            <Skeleton style={{ height: '12px', width: '30%' }} />
            <Skeleton style={{ height: '12px', width: '25%' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function EstadoVazio({ onNovaAnalise }) {
  return (
    <div
      className="rounded-2xl flex flex-col items-center justify-center py-16 px-6 text-center"
      style={{ background: C.fundoCard, border: `1.5px dashed ${C.borda}` }}
    >
      <div className="text-5xl mb-4">🌱</div>
      <h3 className="font-bold text-base mb-2" style={{ color: C.textoClaro }}>
        Nenhuma análise ainda
      </h3>
      <p className="text-sm mb-6 max-w-xs leading-relaxed" style={{ color: C.textoMuted }}>
        Faça sua primeira análise detalhada com equações alométricas regionais e descubra o
        potencial real de carbono da sua propriedade.
      </p>
      <button
        onClick={onNovaAnalise}
        className="px-6 py-3 rounded-xl font-semibold text-sm transition-all hover:opacity-90 active:scale-95"
        style={{ background: C.verde, color: '#fff' }}
      >
        Iniciar primeira análise →
      </button>
    </div>
  )
}

const CONSENTIMENTOS_OPCIONAIS = [
  {
    id: 'banco_fornecedores',
    icone: '🌳',
    rotulo: 'Fornecedor de créditos',
    descricao: 'Seu perfil pode ser conectado a compradores',
  },
  {
    id: 'comprador',
    icone: '💼',
    rotulo: 'Comprador de créditos',
    descricao: 'Interesse em compensar emissões voluntariamente',
  },
  {
    id: 'uniao_areas',
    icone: '🤝',
    rotulo: 'Agrupamento de áreas',
    descricao: 'Busca por propriedades para certificação conjunta',
  },
  {
    id: 'estudo_cientifico',
    icone: '🔬',
    rotulo: 'Estudo científico',
    descricao: 'Dados anonimizados para pesquisa sobre biomassa',
  },
]

function CartaoConsentimentos({ consentimentos, onAlterar }) {
  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
    >
      <h3 className="text-sm font-bold mb-1" style={{ color: C.textoClaro }}>
        Perfil na rede
      </h3>
      <p className="text-xs mb-4" style={{ color: C.textoMuted }}>
        Suas preferências de participação no mercado voluntário.
      </p>
      <div className="space-y-3">
        {CONSENTIMENTOS_OPCIONAIS.map((c) => {
          const ativo = !!consentimentos[c.id]
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onAlterar(c.id)}
              className="w-full flex items-center gap-3 p-3 rounded-xl text-left transition-colors"
              style={{
                background: ativo ? 'rgba(76,175,114,0.07)' : 'transparent',
                border: `1px solid ${ativo ? C.borda : 'transparent'}`,
                cursor: 'pointer',
              }}
            >
              <span className="text-xl flex-shrink-0">{c.icone}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold" style={{ color: ativo ? C.textoClaro : C.textoMuted }}>
                  {c.rotulo}
                </p>
                <p className="text-xs leading-tight mt-0.5" style={{ color: C.textoMuted }}>
                  {c.descricao}
                </p>
              </div>
              <span
                className="text-xs font-semibold flex-shrink-0"
                style={{ color: ativo ? C.verde : C.textoMuted }}
              >
                {ativo ? 'Ativo' : 'Inativo'}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function MensagemMotivacional({ totalTCO2 }) {
  const valorFormatado = totalTCO2 > 0 ? formatarTCO2(totalTCO2) : null
  return (
    <div
      className="rounded-2xl p-5"
      style={{
        background: 'linear-gradient(135deg, #132a16 0%, #1a3a20 100%)',
        border: `1px solid ${C.borda}`,
      }}
    >
      <div className="text-2xl mb-3">🌍</div>
      <h3 className="text-sm font-bold mb-2" style={{ color: C.textoClaro }}>
        {valorFormatado
          ? `Sua terra já mapeou ${valorFormatado}`
          : 'O potencial está na sua terra'}
      </h3>
      <p className="text-xs leading-relaxed" style={{ color: C.textoMuted }}>
        {valorFormatado
          ? 'Cada análise torna o valor climático da sua propriedade mais preciso e verificável. Com metodologia alométrica e elegibilidade documentada, você está mais perto de transformar conservação em receita.'
          : 'A vegetação nativa brasileira já sequestrou mais de 120 bilhões de toneladas de CO₂. Sua propriedade faz parte dessa história — e pode gerar receita com isso através do mercado voluntário de carbono.'}
      </p>
      <div
        className="mt-4 pt-4 text-xs"
        style={{ borderTop: `1px solid ${C.borda}`, color: C.textoMuted }}
      >
        💡 Propriedades acima de 500 ha têm maior elegibilidade para certificação pelo padrão Verra VCS.
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function PaginaPainel() {
  const navegar = useNavigate()

  const [usuario, setUsuario]         = useState(null)
  const [analises, setAnalises]       = useState([])
  const [carregando, setCarregando]   = useState(true)
  const [erroAPI, setErroAPI]         = useState(false)

  const [consentimentos, setConsentimentos] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('carbono_consentimentos') ?? '{}')
    } catch {
      return {}
    }
  })

  // Busca dados do usuário e análises
  const buscarDados = useCallback(async () => {
    setCarregando(true)
    setErroAPI(false)
    try {
      const respUsuario = await api.get('/auth/eu')
      setUsuario(respUsuario.data)

      try {
        const respAnalises = await api.get('/analises/minhas')
        setAnalises(Array.isArray(respAnalises.data) ? respAnalises.data : [])
      } catch {
        // Endpoint ainda não implementado — mostra estado vazio
        setAnalises([])
      }
    } catch {
      setErroAPI(true)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => { buscarDados() }, [buscarDados])

  // Persistir consentimentos opcionais em localStorage
  const alternarConsentimento = (id) => {
    setConsentimentos((prev) => {
      const novo = { ...prev, [id]: !prev[id] }
      localStorage.setItem('carbono_consentimentos', JSON.stringify(novo))
      return novo
    })
  }

  const sair = () => {
    localStorage.removeItem('carbono_token')
    localStorage.removeItem('carbono_consentimentos')
    navegar('/login')
  }

  // Estatísticas derivadas
  const totalAnalises = analises.length
  const maiorTCO2     = analises.reduce((acc, a) => Math.max(acc, a.tco2_estimado ?? 0), 0)
  const totalTCO2     = analises.reduce((acc, a) => acc + (a.tco2_estimado ?? 0), 0)
  const mediaEleg     = (() => {
    if (!analises.length) return '—'
    const contagem = analises.reduce((acc, a) => {
      const k = a.elegibilidade?.toLowerCase()
      acc[k] = (acc[k] ?? 0) + 1
      return acc
    }, {})
    const predominante = Object.entries(contagem).sort((a, b) => b[1] - a[1])[0]?.[0]
    return COR_ELEGIBILIDADE[predominante]?.texto ?? '—'
  })()

  // ── Tela de erro de autenticação ──
  if (erroAPI) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center"
        style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
      >
        <div className="text-4xl mb-4">🔒</div>
        <h2 className="text-lg font-bold mb-2" style={{ color: C.textoClaro }}>
          Sessão expirada
        </h2>
        <p className="text-sm mb-6" style={{ color: C.textoMuted }}>
          Faça login novamente para acessar o painel.
        </p>
        <button
          onClick={() => navegar('/login')}
          className="px-6 py-3 rounded-xl font-semibold text-sm"
          style={{ background: C.verde, color: '#fff' }}
        >
          Ir para o login
        </button>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
    >

      {/* ── Navbar ── */}
      <nav
        className="sticky top-0 z-40 flex items-center justify-between px-5 py-4"
        style={{
          background: 'rgba(13,31,15,0.95)',
          backdropFilter: 'blur(10px)',
          borderBottom: `1px solid ${C.borda}`,
        }}
      >
        <Link
          to="/"
          className="text-lg font-bold tracking-tight"
          style={{ color: C.verde, textDecoration: 'none' }}
        >
          🌱 Carbono em Pé
        </Link>

        <div className="flex items-center gap-3">
          {carregando ? (
            <Skeleton style={{ height: '16px', width: '100px' }} />
          ) : (
            <span className="text-sm hidden sm:block" style={{ color: C.textoMuted }}>
              {usuario?.nome ?? '—'}
            </span>
          )}
          <button
            onClick={sair}
            className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-80"
            style={{
              background: C.fundoCard,
              color: C.textoMuted,
              border: `1px solid ${C.borda}`,
            }}
          >
            Sair
          </button>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-4 py-10">

        {/* ── Boas-vindas ── */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8">
          <div>
            {carregando ? (
              <>
                <Skeleton style={{ height: '32px', width: '220px', marginBottom: '8px' }} />
                <Skeleton style={{ height: '14px', width: '300px' }} />
              </>
            ) : (
              <>
                <h1
                  className="text-3xl sm:text-4xl font-bold"
                  style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
                >
                  Olá, {primeiroNome(usuario?.nome)} 👋
                </h1>
                <p className="mt-1 text-sm" style={{ color: C.textoMuted }}>
                  Acompanhe suas análises e o potencial de carbono da sua propriedade.
                </p>
              </>
            )}
          </div>

          <button
            onClick={() => navegar('/estimativa')}
            className="flex-shrink-0 px-5 py-3 rounded-xl font-bold text-sm transition-all hover:opacity-90 active:scale-95"
            style={{ background: C.verde, color: '#fff' }}
          >
            + Nova análise — Camada 2
          </button>
        </div>

        {/* ── Cartões de resumo ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {carregando ? (
            [1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-2xl p-5"
                style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
              >
                <Skeleton style={{ height: '11px', width: '60%', marginBottom: '12px' }} />
                <Skeleton style={{ height: '28px', width: '40%' }} />
              </div>
            ))
          ) : (
            <>
              <CartaoStat
                rotulo="Análises realizadas"
                valor={totalAnalises}
                sub={totalAnalises === 1 ? '1 análise concluída' : `${totalAnalises} análises concluídas`}
              />
              <CartaoStat
                rotulo="Maior estoque estimado"
                valor={maiorTCO2 > 0 ? formatarTCO2(maiorTCO2) : '—'}
                sub="Camada com maior tCO₂e"
              />
              <CartaoStat
                rotulo="Elegibilidade predominante"
                valor={mediaEleg}
                sub="Média das suas análises"
              />
            </>
          )}
        </div>

        {/* ── Conteúdo principal: lista + sidebar ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Lista de análises (2/3) */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold" style={{ color: C.textoClaro }}>
                Análises anteriores
              </h2>
              {!carregando && totalAnalises > 0 && (
                <span className="text-xs" style={{ color: C.textoMuted }}>
                  {totalAnalises} {totalAnalises === 1 ? 'resultado' : 'resultados'}
                </span>
              )}
            </div>

            {carregando ? (
              <SkeletonLista />
            ) : totalAnalises === 0 ? (
              <EstadoVazio onNovaAnalise={() => navegar('/estimativa')} />
            ) : (
              <div className="space-y-3">
                {analises.map((analise) => {
                  const eleg = COR_ELEGIBILIDADE[analise.elegibilidade?.toLowerCase()]
                  return (
                    <Link
                      key={analise.id}
                      to={`/resultado/${analise.id}`}
                      className="block rounded-2xl p-5 transition-all hover:scale-[1.01]"
                      style={{
                        background: C.fundoCard,
                        border: `1px solid ${C.borda}`,
                        textDecoration: 'none',
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-sm font-bold" style={{ color: C.textoClaro }}>
                              {analise.bioma ?? '—'}
                            </span>
                            <span
                              className="text-xs px-2 py-0.5 rounded-full"
                              style={{ background: C.inputBg, color: C.textoMuted }}
                            >
                              Camada {analise.camada ?? '—'}
                            </span>
                          </div>
                          <p className="text-xs" style={{ color: C.textoMuted }}>
                            {analise.tipo_vegetacao ?? '—'}
                          </p>
                        </div>
                        <BadgeElegibilidade valor={analise.elegibilidade} />
                      </div>

                      <div className="flex items-center gap-5 mt-3 flex-wrap">
                        <div>
                          <p className="text-xs" style={{ color: C.textoMuted }}>Estoque estimado</p>
                          <p className="text-sm font-bold" style={{ color: C.verde }}>
                            {formatarTCO2(analise.tco2_estimado)}
                          </p>
                        </div>
                        {analise.biomassa_tha != null && (
                          <div>
                            <p className="text-xs" style={{ color: C.textoMuted }}>Biomassa</p>
                            <p className="text-sm font-semibold" style={{ color: C.textoClaro }}>
                              {analise.biomassa_tha?.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Mg/ha
                            </p>
                          </div>
                        )}
                        <div className="ml-auto text-right">
                          <p className="text-xs" style={{ color: C.textoMuted }}>
                            {formatarData(analise.criado_em)}
                          </p>
                          <p className="text-xs mt-0.5" style={{ color: C.verde }}>
                            Ver resultado →
                          </p>
                        </div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>

          {/* Sidebar (1/3) */}
          <div className="flex flex-col gap-5">
            <CartaoConsentimentos
              consentimentos={consentimentos}
              onAlterar={alternarConsentimento}
            />
            <MensagemMotivacional totalTCO2={totalTCO2} />
          </div>

        </div>
      </div>
    </div>
  )
}
