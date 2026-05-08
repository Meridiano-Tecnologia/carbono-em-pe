import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
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

function RequisitoseSenha({ senha }) {
  const itens = [
    { texto: '8 ou mais caracteres', ok: senha.length >= 8 },
    { texto: 'Uma letra maiúscula',  ok: /[A-Z]/.test(senha) },
    { texto: 'Uma letra minúscula',  ok: /[a-z]/.test(senha) },
    { texto: 'Um número',            ok: /\d/.test(senha) },
  ]
  if (!senha) return null
  return (
    <div className="grid grid-cols-2 gap-1.5 mt-2">
      {itens.map((r) => (
        <div key={r.texto} className="flex items-center gap-1.5 text-xs">
          <span style={{ color: r.ok ? C.verde : C.textoMuted, fontWeight: 700 }}>
            {r.ok ? '✓' : '○'}
          </span>
          <span style={{ color: r.ok ? C.verde : C.textoMuted }}>{r.texto}</span>
        </div>
      ))}
    </div>
  )
}

export default function PaginaRedefinirSenha() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''

  const [novaSenha, setNovaSenha]       = useState('')
  const [confirmacao, setConfirmacao]   = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [carregando, setCarregando]     = useState(false)
  const [estado, setEstado]             = useState('idle') // idle | sucesso | erro
  const [mensagemErro, setMensagemErro] = useState('')

  const senhaValida  = novaSenha.length >= 8 && /[A-Z]/.test(novaSenha) && /[a-z]/.test(novaSenha) && /\d/.test(novaSenha)
  const senhasIguais = novaSenha === confirmacao && confirmacao !== ''
  const podeSubmeter = !!token && senhaValida && senhasIguais && !carregando

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4"
        style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}>
        <div className="w-full max-w-sm rounded-2xl p-8 text-center"
          style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}>
          <p className="text-sm mb-4" style={{ color: C.erro }}>Link inválido ou expirado.</p>
          <Link to="/esqueci-senha" className="text-sm font-semibold underline"
            style={{ color: C.verde }}>
            Solicitar novo link
          </Link>
        </div>
      </div>
    )
  }

  const handleSubmeter = async (e) => {
    e.preventDefault()
    setMensagemErro('')
    setCarregando(true)
    try {
      await api.post('/auth/redefinir-senha', { token, nova_senha: novaSenha })
      setEstado('sucesso')
    } catch (err) {
      const detalhe = err.response?.data?.detail
      if (err.response?.status === 400) {
        setEstado('erro')
      } else {
        setMensagemErro(
          typeof detalhe === 'string' ? detalhe : 'Não foi possível redefinir a senha. Tente novamente.'
        )
      }
    } finally {
      setCarregando(false)
    }
  }

  if (estado === 'sucesso') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4"
        style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}>
        <div className="w-full max-w-sm rounded-2xl p-8 text-center"
          style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}>
          <div className="flex items-center justify-center w-14 h-14 rounded-full mx-auto mb-5"
            style={{ background: 'rgba(76,175,114,0.15)', border: `2px solid ${C.verde}` }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
              stroke={C.verde} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-3"
            style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}>
            Senha redefinida!
          </h2>
          <p className="text-sm mb-6" style={{ color: C.textoMuted }}>
            Sua senha foi atualizada com sucesso. Faça login para continuar.
          </p>
          <Link to="/login"
            className="block w-full py-3.5 rounded-xl font-bold text-sm text-center hover:opacity-90 transition-all"
            style={{ background: C.verde, color: '#fff', textDecoration: 'none' }}>
            Ir para o login →
          </Link>
        </div>
      </div>
    )
  }

  if (estado === 'erro') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4"
        style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}>
        <div className="w-full max-w-sm rounded-2xl p-8 text-center"
          style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}>
          <p className="text-sm mb-2" style={{ color: C.erro }}>Link inválido ou expirado.</p>
          <p className="text-xs mb-6" style={{ color: C.textoMuted }}>
            O link de redefinição tem validade de 15 minutos e só pode ser usado uma vez.
          </p>
          <Link to="/esqueci-senha"
            className="block w-full py-3.5 rounded-xl font-bold text-sm text-center hover:opacity-90 transition-all"
            style={{ background: C.verde, color: '#fff', textDecoration: 'none' }}>
            Solicitar novo link →
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}>
      <nav className="flex items-center px-5 py-4"
        style={{
          background: 'rgba(13,31,15,0.92)',
          backdropFilter: 'blur(10px)',
          borderBottom: `1px solid ${C.borda}`,
        }}>
        <Link to="/" className="text-lg font-bold tracking-tight"
          style={{ color: C.verde, textDecoration: 'none' }}>
          🌱 Carbono em Pé
        </Link>
      </nav>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2"
              style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}>
              Nova senha
            </h1>
            <p className="text-sm" style={{ color: C.textoMuted }}>
              Escolha uma senha forte para sua conta.
            </p>
          </div>

          <form onSubmit={handleSubmeter} noValidate
            className="rounded-2xl p-6"
            style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}>

            {/* Nova senha */}
            <div className="mb-4">
              <label htmlFor="nova-senha" className="block text-sm font-semibold mb-1.5"
                style={{ color: C.textoClaro }}>
                Nova senha
              </label>
              <div className="relative">
                <input
                  id="nova-senha"
                  type={mostrarSenha ? 'text' : 'password'}
                  value={novaSenha}
                  onChange={(e) => setNovaSenha(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  required
                  className="w-full rounded-xl px-4 py-3 text-sm outline-none"
                  style={{
                    background: C.inputBg,
                    color: C.textoClaro,
                    border: `1px solid ${C.bordaInput}`,
                    paddingRight: '80px',
                  }}
                />
                <button type="button" onClick={() => setMostrarSenha((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold"
                  style={{ color: C.textoMuted, background: 'none', border: 'none', cursor: 'pointer' }}>
                  {mostrarSenha ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
              <RequisitoseSenha senha={novaSenha} />
            </div>

            {/* Confirmação */}
            <div className="mb-5">
              <label htmlFor="confirmacao" className="block text-sm font-semibold mb-1.5"
                style={{ color: C.textoClaro }}>
                Confirme a senha
              </label>
              <input
                id="confirmacao"
                type={mostrarSenha ? 'text' : 'password'}
                value={confirmacao}
                onChange={(e) => setConfirmacao(e.target.value)}
                placeholder="Repita a senha"
                required
                className="w-full rounded-xl px-4 py-3 text-sm outline-none"
                style={{
                  background: C.inputBg,
                  color: C.textoClaro,
                  border: `1px solid ${confirmacao && !senhasIguais ? C.erro : C.bordaInput}`,
                }}
              />
              {confirmacao && !senhasIguais && (
                <p className="text-xs mt-1.5" style={{ color: C.erro }}>As senhas não coincidem.</p>
              )}
              {confirmacao && senhasIguais && (
                <p className="text-xs mt-1.5" style={{ color: C.verde }}>✓ Senhas conferem.</p>
              )}
            </div>

            {mensagemErro && (
              <div className="rounded-xl px-4 py-3 mb-4 text-sm"
                style={{ background: C.erroFundo, color: C.erro, border: '1px solid #5c1a1a' }}>
                {mensagemErro}
              </div>
            )}

            <button type="submit" disabled={!podeSubmeter}
              className="w-full py-3.5 rounded-xl font-bold text-sm transition-all"
              style={{
                background: podeSubmeter ? C.verde : C.inputBg,
                color: podeSubmeter ? '#fff' : C.textoMuted,
                cursor: podeSubmeter ? 'pointer' : 'not-allowed',
                border: `1px solid ${podeSubmeter ? C.verde : C.borda}`,
              }}>
              {carregando ? 'Salvando…' : 'Redefinir senha →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
