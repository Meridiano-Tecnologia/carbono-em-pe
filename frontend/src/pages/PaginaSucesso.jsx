import { useEffect, useState } from 'react'
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

const LABEL_CAMADA = {
  1: 'Camada 1 — Estimativa IPCC (gratuita)',
  2: 'Camada 2 — Análise alométrica regional',
  3: 'Camada 3 — Análise avançada por área',
}

function formatarValor(centavos) {
  return (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function IconeCheck() {
  return (
    <div
      className="flex items-center justify-center w-16 h-16 rounded-full mx-auto mb-6"
      style={{ background: 'rgba(76,175,114,0.15)', border: `2px solid ${C.verde}` }}
    >
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
        stroke={C.verde} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <div
        className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin"
        style={{ borderColor: `${C.verde} transparent ${C.verde} ${C.verde}` }}
      />
      <p className="text-sm" style={{ color: C.textoMuted }}>Verificando pagamento…</p>
    </div>
  )
}

function BotaoPainel() {
  return (
    <Link
      to="/painel"
      className="block w-full py-3.5 rounded-xl font-bold text-sm text-center transition-all hover:opacity-90 mt-6"
      style={{ background: C.verde, color: '#fff', textDecoration: 'none' }}
    >
      Ir para o painel →
    </Link>
  )
}

export default function PaginaSucesso() {
  const [params] = useSearchParams()
  const sessaoId = params.get('sessao')

  const [estado, setEstado] = useState('carregando') // carregando | sucesso | fallback
  const [dados, setDados]   = useState(null)

  useEffect(() => {
    if (!sessaoId) {
      setEstado('fallback')
      return
    }

    api.get(`/pagamento/sessao/${sessaoId}`)
      .then(({ data }) => {
        setDados(data)
        setEstado('sucesso')
      })
      .catch(() => {
        // Webhook pode ainda estar processando — exibe mensagem genérica
        setEstado('fallback')
      })
  }, [sessaoId])

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
    >
      <div
        className="w-full max-w-md rounded-2xl p-10 text-center"
        style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
      >
        {estado === 'carregando' && <Spinner />}

        {estado === 'sucesso' && dados && (
          <>
            <IconeCheck />

            <h1 className="text-2xl font-bold mb-2" style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}>
              Pagamento confirmado!
            </h1>

            <p className="text-sm mb-6" style={{ color: C.textoMuted, lineHeight: '1.6' }}>
              Seu relatório está sendo gerado e será enviado em breve.
            </p>

            <div
              className="rounded-xl p-4 text-left space-y-3 mb-2"
              style={{ background: C.fundoEscuro, border: `1px solid ${C.borda}` }}
            >
              <div className="flex justify-between text-sm">
                <span style={{ color: C.textoMuted }}>Tipo de análise</span>
                <span className="font-semibold text-right" style={{ color: C.textoClaro }}>
                  {LABEL_CAMADA[dados.camada] ?? `Camada ${dados.camada}`}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span style={{ color: C.textoMuted }}>Valor pago</span>
                <span className="font-bold" style={{ color: C.verde }}>
                  {formatarValor(dados.valor_centavos)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span style={{ color: C.textoMuted }}>Status</span>
                <span className="font-semibold" style={{ color: C.verde }}>
                  {dados.status === 'confirmado' ? 'Confirmado' : 'Processando'}
                </span>
              </div>
            </div>

            <BotaoPainel />
          </>
        )}

        {estado === 'fallback' && (
          <>
            <IconeCheck />

            <h1 className="text-2xl font-bold mb-3" style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}>
              Pagamento confirmado!
            </h1>

            <p className="text-sm mb-6" style={{ color: C.textoMuted, lineHeight: '1.6' }}>
              Seu pagamento foi recebido com sucesso. Seu relatório está sendo gerado
              e será disponibilizado no painel em instantes.
            </p>

            <BotaoPainel />
          </>
        )}
      </div>
    </div>
  )
}
