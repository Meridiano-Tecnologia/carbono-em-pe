import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

const C = {
  fundoEscuro: '#0d1f0f',
  fundoCard:   '#132a16',
  borda:       '#1e4024',
  bordaInput:  '#234527',
  inputBg:     '#1a3320',
  verde:       '#4caf72',
  textoClaro:  '#e8f5ed',
  textoMuted:  '#86a98c',
  erro:        '#ef4444',
  erroFundo:   '#2d0f0f',
}

export default function PaginaEsqueciSenha() {
  const [email, setEmail]       = useState('')
  const [carregando, setCarregando] = useState(false)
  const [enviado, setEnviado]   = useState(false)
  const [erro, setErro]         = useState('')

  const podeSubmeter = email.trim() !== '' && !carregando

  const handleSubmeter = async (e) => {
    e.preventDefault()
    setErro('')
    setCarregando(true)
    try {
      await api.post('/auth/esqueci-senha', { email: email.trim() })
      setEnviado(true)
    } catch {
      setErro('Não foi possível processar a solicitação. Tente novamente.')
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
        <Link to="/" className="text-lg font-bold tracking-tight"
          style={{ color: C.verde, textDecoration: 'none' }}>
          🌱 Carbono em Pé
        </Link>
      </nav>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">

          {!enviado ? (
            <>
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold mb-2"
                  style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}>
                  Esqueci minha senha
                </h1>
                <p className="text-sm" style={{ color: C.textoMuted }}>
                  Informe seu e-mail e enviaremos um link de redefinição.
                </p>
              </div>

              <form
                onSubmit={handleSubmeter}
                noValidate
                className="rounded-2xl p-6"
                style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
              >
                <div className="mb-5">
                  <label htmlFor="email" className="block text-sm font-semibold mb-1.5"
                    style={{ color: C.textoClaro }}>
                    E-mail
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="seu@email.com.br"
                    autoComplete="email"
                    required
                    className="w-full rounded-xl px-4 py-3 text-sm outline-none"
                    style={{
                      background: C.inputBg,
                      color: C.textoClaro,
                      border: `1px solid ${C.bordaInput}`,
                    }}
                  />
                </div>

                {erro && (
                  <div className="rounded-xl px-4 py-3 mb-4 text-sm"
                    style={{ background: C.erroFundo, color: C.erro, border: '1px solid #5c1a1a' }}>
                    {erro}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!podeSubmeter}
                  className="w-full py-3.5 rounded-xl font-bold text-sm transition-all"
                  style={{
                    background: podeSubmeter ? C.verde : C.inputBg,
                    color: podeSubmeter ? '#fff' : C.textoMuted,
                    cursor: podeSubmeter ? 'pointer' : 'not-allowed',
                    border: `1px solid ${podeSubmeter ? C.verde : C.borda}`,
                  }}
                >
                  {carregando ? 'Enviando…' : 'Enviar instruções →'}
                </button>
              </form>
            </>
          ) : (
            <div className="rounded-2xl p-8 text-center"
              style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}>
              <div className="flex items-center justify-center w-14 h-14 rounded-full mx-auto mb-5"
                style={{ background: 'rgba(76,175,114,0.15)', border: `2px solid ${C.verde}` }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
                  stroke={C.verde} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
              </div>
              <h2 className="text-xl font-bold mb-3"
                style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}>
                Verifique seu e-mail
              </h2>
              <p className="text-sm mb-6" style={{ color: C.textoMuted, lineHeight: '1.6' }}>
                Se o endereço <strong style={{ color: C.textoClaro }}>{email}</strong> estiver
                cadastrado, você receberá as instruções em breve.
                O link expira em <strong style={{ color: C.textoClaro }}>15 minutos</strong>.
              </p>
              <p className="text-xs" style={{ color: C.textoMuted }}>
                Não recebeu?{' '}
                <button type="button" onClick={() => setEnviado(false)}
                  className="underline font-semibold"
                  style={{ color: C.verde, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                  Tentar novamente
                </button>
              </p>
            </div>
          )}

          <p className="text-sm text-center mt-6" style={{ color: C.textoMuted }}>
            <Link to="/login" className="font-semibold underline hover:opacity-75"
              style={{ color: C.verde }}>
              ← Voltar para o login
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
