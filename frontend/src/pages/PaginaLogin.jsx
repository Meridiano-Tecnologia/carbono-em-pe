import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'

// ─── Paleta ───────────────────────────────────────────────────────────────────

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

// ─── Componente principal ─────────────────────────────────────────────────────

export default function PaginaLogin() {
  const navegar = useNavigate()

  const [email, setEmail]               = useState('')
  const [senha, setSenha]               = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [carregando, setCarregando]     = useState(false)
  const [mensagemErro, setMensagemErro] = useState('')

  const podeSubmeter = email.trim() !== '' && senha !== '' && !carregando

  const handleSubmeter = async (e) => {
    e.preventDefault()
    setMensagemErro('')
    setCarregando(true)

    try {
      const resposta = await api.post('/auth/login', { email: email.trim(), senha })
      localStorage.setItem('carbono_token', resposta.data.token_acesso)
      navegar('/painel')
    } catch (err) {
      const detalhe = err.response?.data?.detail
      setMensagemErro(
        typeof detalhe === 'string'
          ? detalhe
          : 'Não foi possível entrar. Verifique sua conexão e tente novamente.'
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

      {/* ── Navbar ── */}
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
        <Link
          to="/cadastro"
          className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90"
          style={{
            background: C.fundoCard,
            color: C.verde,
            border: `1px solid ${C.borda}`,
            textDecoration: 'none',
          }}
        >
          Criar conta
        </Link>
      </nav>

      {/* ── Conteúdo central ── */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">

          {/* Cabeçalho */}
          <div className="text-center mb-8">
            <span
              className="inline-block text-xs font-semibold uppercase tracking-widest px-4 py-1.5 rounded-full mb-4"
              style={{ background: C.fundoCard, color: C.verde, border: `1px solid ${C.borda}` }}
            >
              Acesso à plataforma
            </span>
            <h1
              className="text-3xl font-bold mb-2"
              style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
            >
              Entrar na sua conta
            </h1>
            <p className="text-sm" style={{ color: C.textoMuted }}>
              Acesse seu painel e suas análises de carbono.
            </p>
          </div>

          {/* Card do formulário */}
          <form
            onSubmit={handleSubmeter}
            noValidate
            className="rounded-2xl p-6"
            style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
          >
            {/* E-mail */}
            <div className="mb-4">
              <label
                htmlFor="email"
                className="block text-sm font-semibold mb-1.5"
                style={{ color: C.textoClaro }}
              >
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

            {/* Senha */}
            <div className="mb-6">
              <label
                htmlFor="senha"
                className="block text-sm font-semibold mb-1.5"
                style={{ color: C.textoClaro }}
              >
                Senha
              </label>
              <div className="relative">
                <input
                  id="senha"
                  type={mostrarSenha ? 'text' : 'password'}
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Sua senha"
                  autoComplete="current-password"
                  required
                  className="w-full rounded-xl px-4 py-3 text-sm outline-none"
                  style={{
                    background: C.inputBg,
                    color: C.textoClaro,
                    border: `1px solid ${C.bordaInput}`,
                    paddingRight: '80px',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setMostrarSenha((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold"
                  style={{ color: C.textoMuted, background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  {mostrarSenha ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </div>

            {/* Esqueci minha senha */}
            <div className="text-right mb-5" style={{ marginTop: '-12px' }}>
              <Link
                to="/esqueci-senha"
                className="text-xs font-semibold underline transition-opacity hover:opacity-75"
                style={{ color: C.textoMuted }}
              >
                Esqueci minha senha
              </Link>
            </div>

            {/* Mensagem de erro */}
            {mensagemErro && (
              <div
                className="rounded-xl px-4 py-3 mb-4 text-sm"
                style={{ background: C.erroFundo, color: C.erro, border: '1px solid #5c1a1a' }}
              >
                {mensagemErro}
              </div>
            )}

            {/* Botão */}
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
              {carregando ? 'Entrando…' : 'Entrar →'}
            </button>
          </form>

          {/* Link para cadastro */}
          <p className="text-sm text-center mt-6" style={{ color: C.textoMuted }}>
            Ainda não tem conta?{' '}
            <Link
              to="/cadastro"
              className="font-semibold underline transition-opacity hover:opacity-75"
              style={{ color: C.verde }}
            >
              Cadastre-se gratuitamente
            </Link>
          </p>

        </div>
      </div>
    </div>
  )
}
