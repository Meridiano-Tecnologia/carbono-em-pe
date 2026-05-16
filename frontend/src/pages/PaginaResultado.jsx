import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../services/api'

const C = {
  fundoEscuro: '#0d1f0f',
  fundoCard:   '#132a16',
  borda:       '#1e4024',
  inputBg:     '#1a3320',
  verde:       '#4caf72',
  textoClaro:  '#e8f5ed',
  textoMuted:  '#86a98c',
  erro:        '#ef4444',
  erroFundo:   '#2d0f0f',
}

const COR_ELEGIBILIDADE = {
  alto:  { texto: 'Alto',  cor: '#4caf72', fundo: 'rgba(76,175,114,0.12)' },
  medio: { texto: 'Médio', cor: '#f59e0b', fundo: 'rgba(245,158,11,0.12)' },
  baixo: { texto: 'Baixo', cor: '#ef4444', fundo: 'rgba(239,68,68,0.12)'  },
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

function CartaoInfo({ rotulo, valor, destaque = false }) {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-1"
      style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
    >
      <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: C.textoMuted }}>
        {rotulo}
      </p>
      <p className="text-xl font-bold" style={{ color: destaque ? C.verde : C.textoClaro }}>
        {valor ?? '—'}
      </p>
    </div>
  )
}

export default function PaginaResultado() {
  const { analise_id } = useParams()
  const token = localStorage.getItem('carbono_token')

  const [analise, setAnalise]     = useState(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro]           = useState('')

  useEffect(() => {
    async function buscar() {
      try {
        const { data } = await api.get(`/analises/${analise_id}`)
        setAnalise(data)
      } catch (err) {
        setErro(
          err.response?.status === 404
            ? 'Análise não encontrada.'
            : 'Erro ao carregar os dados da análise.'
        )
      } finally {
        setCarregando(false)
      }
    }
    buscar()
  }, [analise_id])

  const eleg = COR_ELEGIBILIDADE[analise?.elegibilidade?.toLowerCase()]

  return (
    <div
      className="min-h-screen"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
    >
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
        {token && (
          <Link
            to="/painel"
            className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90"
            style={{
              background: C.fundoCard,
              color: C.verde,
              border: `1px solid ${C.borda}`,
              textDecoration: 'none',
            }}
          >
            Painel →
          </Link>
        )}
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-10">
        {carregando && (
          <div className="flex items-center justify-center py-20">
            <p className="text-sm" style={{ color: C.textoMuted }}>Carregando análise…</p>
          </div>
        )}

        {!carregando && erro && (
          <div
            className="rounded-xl px-4 py-3 text-sm"
            style={{ background: C.erroFundo, color: C.erro, border: '1px solid #5c1a1a' }}
          >
            {erro}
          </div>
        )}

        {!carregando && analise && (
          <>
            <div className="flex items-center gap-3 mb-6 flex-wrap">
              <span
                className="inline-block text-xs font-semibold uppercase tracking-widest px-3 py-1 rounded-full"
                style={{ background: C.fundoCard, color: C.verde, border: `1px solid ${C.borda}` }}
              >
                Camada {analise.camada ?? '—'}
              </span>
              {eleg && (
                <span
                  className="text-xs font-semibold px-2.5 py-1 rounded-full"
                  style={{ background: eleg.fundo, color: eleg.cor }}
                >
                  Elegibilidade {eleg.texto}
                </span>
              )}
            </div>

            <h1
              className="text-3xl font-bold mb-1"
              style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
            >
              {analise.bioma ?? 'Resultado da Análise'}
            </h1>
            <p className="text-sm mb-8" style={{ color: C.textoMuted }}>
              {[analise.tipo_vegetacao, formatarData(analise.criado_em)].filter(Boolean).join(' · ')}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <CartaoInfo
                rotulo="Estoque estimado"
                valor={formatarTCO2(analise.tco2_estimado)}
                destaque
              />
              {analise.biomassa_tha != null && (
                <CartaoInfo
                  rotulo="Biomassa"
                  valor={`${analise.biomassa_tha.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Mg/ha`}
                />
              )}
              {analise.area_hectares != null && (
                <CartaoInfo
                  rotulo="Área"
                  valor={`${analise.area_hectares.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ha`}
                />
              )}
              {analise.estado && (
                <CartaoInfo rotulo="Estado" valor={analise.estado} />
              )}
            </div>

            {analise.url_relatorio_pdf && (
              <a
                href={analise.url_relatorio_pdf}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full py-3.5 rounded-xl font-bold text-sm text-center transition-all hover:opacity-90 mb-4"
                style={{ background: C.verde, color: '#fff', textDecoration: 'none' }}
              >
                Baixar relatório PDF →
              </a>
            )}

            <Link
              to="/painel"
              className="block w-full py-3 rounded-xl font-semibold text-sm text-center transition-all hover:opacity-80"
              style={{
                background: 'transparent',
                color: C.textoMuted,
                border: `1px solid ${C.borda}`,
                textDecoration: 'none',
              }}
            >
              ← Voltar ao painel
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
