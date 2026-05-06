import { Link } from 'react-router-dom'

const C = {
  fundoEscuro: '#0d1f0f',
  fundoCard:   '#132a16',
  borda:       '#1e4024',
  verde:       '#4caf72',
  textoClaro:  '#e8f5ed',
  textoMuted:  '#86a98c',
}

export default function PaginaSucesso() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
    >
      <div
        className="w-full max-w-md rounded-2xl p-10 text-center"
        style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
      >
        <div
          className="flex items-center justify-center w-16 h-16 rounded-full mx-auto mb-6"
          style={{ background: 'rgba(76,175,114,0.15)', border: `2px solid ${C.verde}` }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke={C.verde}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>

        <h1
          className="text-2xl font-bold mb-3"
          style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
        >
          Pagamento confirmado!
        </h1>

        <p className="text-sm mb-8" style={{ color: C.textoMuted, lineHeight: '1.6' }}>
          Seu relatório está sendo gerado e será enviado em breve.
        </p>

        <Link
          to="/painel"
          className="block w-full py-3.5 rounded-xl font-bold text-sm transition-all hover:opacity-90"
          style={{
            background: C.verde,
            color: '#fff',
            textDecoration: 'none',
          }}
        >
          Ir para o painel →
        </Link>
      </div>
    </div>
  )
}
