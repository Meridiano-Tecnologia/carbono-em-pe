import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'

const C = {
  fundoEscuro: '#0d1f0f',
  fundoCard:   '#132a16',
  borda:       '#1e4024',
  verde:       '#4caf72',
  textoClaro:  '#e8f5ed',
  textoMuted:  '#86a98c',
  erro:        '#ef4444',
  erroFundo:   '#2d0f0f',
}

export default function PaginaEstimativa() {
  const [params] = useSearchParams()
  const analiseIdParam = params.get('analise_id')
  const token = localStorage.getItem('carbono_token')

  const [analiseId, setAnaliseId]           = useState(analiseIdParam)
  const [carregando, setCarregando]         = useState(false)
  const [carregandoAnalise, setCarregandoAnalise] = useState(!analiseIdParam && !!token)
  const [erro, setErro]                     = useState('')

  useEffect(() => {
    if (analiseIdParam || !token) return
    api.get('/analises/minhas')
      .then(({ data }) => {
        const lista = Array.isArray(data) ? data : []
        if (lista.length > 0) setAnaliseId(lista[0].id)
      })
      .catch(() => {})
      .finally(() => setCarregandoAnalise(false))
  }, [analiseIdParam, token])

  const avancar = async () => {
    if (!analiseId) return
    setErro('')
    setCarregando(true)

    try {
      const { data } = await api.post('/pagamento/criar-sessao', {
        analise_id: analiseId,
        camada: 2,
      })
      window.location.href = data.url_checkout
    } catch (err) {
      const detalhe = err.response?.data?.detail
      setErro(
        typeof detalhe === 'string'
          ? detalhe
          : 'Não foi possível iniciar o pagamento. Tente novamente.'
      )
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
    >
      <nav
        className="flex items-center justify-between px-5 py-4"
        style={{
          background: 'rgba(13,31,15,0.92)',
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
        {!token && (
          <Link
            to="/login"
            className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90"
            style={{
              background: C.fundoCard,
              color: C.verde,
              border: `1px solid ${C.borda}`,
              textDecoration: 'none',
            }}
          >
            Entrar
          </Link>
        )}
      </nav>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div
            className="rounded-2xl p-8"
            style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
          >
            <span
              className="inline-block text-xs font-semibold uppercase tracking-widest px-3 py-1 rounded-full mb-5"
              style={{ background: C.fundoEscuro, color: C.verde, border: `1px solid ${C.borda}` }}
            >
              Análise detalhada — Camada 2
            </span>

            <h1
              className="text-2xl font-bold mb-3"
              style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
            >
              Aprofunde sua análise de carbono
            </h1>

            <p className="text-sm mb-6" style={{ color: C.textoMuted, lineHeight: '1.6' }}>
              A Camada 2 usa equações alométricas regionais (Chave et al. 2005) e
              pontuação de elegibilidade em quatro dimensões para o mercado voluntário
              de carbono — fornecendo um laudo muito mais preciso do potencial da sua
              propriedade.
            </p>

            {!carregandoAnalise && !analiseId && (
              <div
                className="rounded-xl px-4 py-3 mb-4 text-sm"
                style={{ background: C.erroFundo, color: C.erro, border: '1px solid #5c1a1a' }}
              >
                Nenhuma análise identificada. Volte ao{' '}
                <Link to="/painel" style={{ color: C.erro, fontWeight: 600 }}>
                  painel
                </Link>{' '}
                e inicie uma nova análise.
              </div>
            )}

            {!token ? (
              <div className="text-center">
                <p className="text-sm mb-4" style={{ color: C.textoMuted }}>
                  Faça login para prosseguir com a análise detalhada.
                </p>
                <Link
                  to={`/login${analiseId ? `?next=/estimativa?analise_id=${analiseId}` : ''}`}
                  className="block w-full py-3.5 rounded-xl font-bold text-sm text-center transition-all hover:opacity-90"
                  style={{
                    background: C.verde,
                    color: '#fff',
                    textDecoration: 'none',
                  }}
                >
                  Entrar para continuar →
                </Link>
              </div>
            ) : (
              <>
                {erro && (
                  <div
                    className="rounded-xl px-4 py-3 mb-4 text-sm"
                    style={{ background: C.erroFundo, color: C.erro, border: '1px solid #5c1a1a' }}
                  >
                    {erro}
                  </div>
                )}

                <button
                  onClick={avancar}
                  disabled={carregando || !analiseId}
                  className="w-full py-3.5 rounded-xl font-bold text-sm transition-all"
                  style={{
                    background: carregando || !analiseId ? '#1a3320' : C.verde,
                    color: carregando || !analiseId ? C.textoMuted : '#fff',
                    border: `1px solid ${carregando || !analiseId ? C.borda : C.verde}`,
                    cursor: carregando || !analiseId ? 'not-allowed' : 'pointer',
                  }}
                >
                  {carregando ? 'Aguarde…' : 'Avançar para análise detalhada — R$ 19'}
                </button>

                <p className="text-xs text-center mt-4" style={{ color: C.textoMuted }}>
                  Pagamento seguro via Stripe. Você será redirecionado ao checkout.
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
