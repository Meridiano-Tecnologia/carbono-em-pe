import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'

// ─── Paleta (idêntica à PaginaInicial) ───────────────────────────────────────

const C = {
  fundoEscuro: '#0d1f0f',
  fundoCard:   '#132a16',
  fundoModal:  '#0f2312',
  borda:       '#1e4024',
  bordaInput:  '#234527',
  inputBg:     '#1a3320',
  verde:       '#4caf72',
  textoClaro:  '#e8f5ed',
  textoMuted:  '#86a98c',
  erro:        '#ef4444',
  erroFundo:   '#2d0f0f',
}

// ─── Definição dos consentimentos ────────────────────────────────────────────

const CONSENTIMENTOS = [
  {
    id: 'termos',
    obrigatorio: true,
    temModal: true,
    texto:
      'Li e concordo com os Termos de uso e Política de privacidade da plataforma Carbono em Pé.',
  },
  {
    id: 'dados_tecnicos',
    obrigatorio: true,
    temModal: false,
    texto:
      'Autorizo a coleta dos dados ambientais informados nesta plataforma para fins de estimativa técnica e melhoria dos algoritmos, de forma anonimizada.',
  },
  {
    id: 'banco_fornecedores',
    obrigatorio: false,
    temModal: false,
    texto:
      'Aceito que meu perfil de propriedade componha um banco de dados de potenciais fornecedores de crédito de carbono em pé — carbono estocado em biomassa aérea de vegetação nativa ainda em pé — para conexão com potenciais compradores e parceiros em oportunidades futuras de comercialização voluntária.',
  },
  {
    id: 'comprador',
    obrigatorio: false,
    temModal: false,
    texto:
      'Tenho interesse em ser contactado como potencial comprador de créditos de carbono em pé para fins de compensação voluntária de emissões.',
  },
  {
    id: 'uniao_areas',
    obrigatorio: false,
    temModal: false,
    texto:
      'Tenho interesse em conhecer outras propriedades com perfil semelhante para avaliar a viabilidade de unir áreas e alcançar escala mínima para certificação conjunta de créditos de carbono em pé.',
  },
  {
    id: 'estudo_cientifico',
    obrigatorio: false,
    temModal: false,
    texto:
      'Autorizo o uso dos meus dados anonimizados para elaboração de estudo científico sobre potencial de geração de créditos de carbono em biomassa aérea no Brasil — meus dados nunca serão publicados de forma identificável.',
  },
]

// ─── Subcomponentes ───────────────────────────────────────────────────────────

function NavbarCadastro() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 py-4"
      style={{
        background: 'rgba(13,31,15,0.92)',
        backdropFilter: 'blur(10px)',
        borderBottom: `1px solid ${C.borda}`,
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      <Link
        to="/"
        className="text-lg font-bold tracking-tight"
        style={{ color: C.verde, textDecoration: 'none' }}
      >
        🌱 Carbono em Pé
      </Link>
      <div className="flex items-center gap-5">
        <span className="text-sm hidden sm:block" style={{ color: C.textoMuted }}>
          Já tem conta?
        </span>
        <Link
          to="/login"
          className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90"
          style={{ background: C.fundoCard, color: C.verde, border: `1px solid ${C.borda}`, textDecoration: 'none' }}
        >
          Entrar
        </Link>
      </div>
    </nav>
  )
}

function Toggle({ marcado, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={marcado}
      onClick={() => onChange(!marcado)}
      className="relative inline-flex items-center rounded-full flex-shrink-0 transition-colors duration-200 focus:outline-none"
      style={{
        width: '42px',
        height: '24px',
        background: marcado ? C.verde : C.inputBg,
        border: `1.5px solid ${marcado ? C.verde : C.borda}`,
      }}
    >
      <span
        className="inline-block rounded-full bg-white shadow transition-transform duration-200"
        style={{
          width: '16px',
          height: '16px',
          transform: marcado ? 'translateX(19px)' : 'translateX(3px)',
        }}
      />
    </button>
  )
}

function ItemConsentimento({ consentimento, marcado, onChange, onAbrirModal }) {
  return (
    <div
      className="flex items-start gap-3 p-4 rounded-xl transition-colors"
      style={{
        background: marcado ? 'rgba(76,175,114,0.06)' : 'transparent',
        border: `1px solid ${marcado ? C.borda : 'transparent'}`,
      }}
    >
      <Toggle marcado={marcado} onChange={onChange} />
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-relaxed" style={{ color: C.textoClaro }}>
          {consentimento.texto}
          {consentimento.temModal && (
            <>
              {' '}
              <button
                type="button"
                onClick={onAbrirModal}
                className="underline font-semibold transition-opacity hover:opacity-75"
                style={{ color: C.verde, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              >
                Ler política completa
              </button>
            </>
          )}
        </p>
        {consentimento.obrigatorio && (
          <span className="text-xs font-semibold mt-1 inline-block" style={{ color: C.verde }}>
            Obrigatório
          </span>
        )}
      </div>
    </div>
  )
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

function CampoTexto({ rotulo, tipo = 'text', valor, onChange, placeholder, obrigatorio = true, botaoLateral }) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-semibold mb-1.5" style={{ color: C.textoClaro }}>
        {rotulo}{' '}
        {!obrigatorio && (
          <span className="font-normal" style={{ color: C.textoMuted }}>(opcional)</span>
        )}
      </label>
      <div className="relative">
        <input
          type={tipo}
          value={valor}
          onChange={onChange}
          placeholder={placeholder}
          required={obrigatorio}
          className="w-full rounded-xl px-4 py-3 text-sm outline-none"
          style={{
            background: C.inputBg,
            color: C.textoClaro,
            border: `1px solid ${C.bordaInput}`,
            paddingRight: botaoLateral ? '80px' : undefined,
          }}
        />
        {botaoLateral && (
          <button
            type="button"
            onClick={botaoLateral.onClick}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold"
            style={{ color: C.textoMuted, background: 'none', border: 'none', cursor: 'pointer' }}
          >
            {botaoLateral.rotulo}
          </button>
        )}
      </div>
    </div>
  )
}

function ModalPolitica({ onFechar }) {
  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onFechar() }}
    >
      <div
        className="relative w-full max-w-xl rounded-2xl flex flex-col"
        style={{
          background: C.fundoCard,
          border: `1px solid ${C.borda}`,
          maxHeight: '85vh',
          fontFamily: "'DM Sans', sans-serif",
        }}
      >
        {/* Cabeçalho do modal */}
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderBottom: `1px solid ${C.borda}` }}
        >
          <h2 className="text-base font-bold" style={{ color: C.textoClaro }}>
            Política de Privacidade — Carbono em Pé
          </h2>
          <button
            type="button"
            onClick={onFechar}
            className="text-xl leading-none transition-opacity hover:opacity-60"
            style={{ color: C.textoMuted, background: 'none', border: 'none', cursor: 'pointer' }}
            aria-label="Fechar"
          >
            ×
          </button>
        </div>

        {/* Corpo do modal com scroll */}
        <div className="overflow-y-auto px-6 py-5 space-y-6 text-sm leading-relaxed" style={{ color: C.textoMuted }}>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              1. Identificação da Controladora
            </h3>
            <p>
              <strong style={{ color: C.textoClaro }}>Nome:</strong> Meridiano Tecnologia<br />
              <strong style={{ color: C.textoClaro }}>CNPJ:</strong> 66.298.885/0001-65<br />
              <strong style={{ color: C.textoClaro }}>Sede:</strong> Rua País Leme, 215, Conj. 1713, Pinheiros, São Paulo/SP, CEP 05.424-150<br />
              <strong style={{ color: C.textoClaro }}>Contato DPO:</strong>{' '}
              <a href="mailto:privacidade@meridianotecnologia.com.br" style={{ color: C.verde }}>
                privacidade@meridianotecnologia.com.br
              </a>
            </p>
          </section>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              2. Dados Coletados
            </h3>
            <ul className="list-disc pl-4 space-y-1">
              <li><strong style={{ color: C.textoClaro }}>Cadastrais:</strong> nome completo, endereço de e-mail e telefone.</li>
              <li><strong style={{ color: C.textoClaro }}>Ambientais:</strong> bioma, tipo de vegetação, área em hectares, idade estimada da vegetação e localização geográfica (quando informada).</li>
              <li><strong style={{ color: C.textoClaro }}>Técnicos:</strong> resultados das estimativas de tCO₂ e pontuações de elegibilidade geradas pela plataforma.</li>
              <li><strong style={{ color: C.textoClaro }}>Consentimentos:</strong> registro das escolhas de consentimento com data e hora.</li>
            </ul>
          </section>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              3. Finalidades do Tratamento
            </h3>
            <ul className="list-disc pl-4 space-y-1">
              <li>Prestação dos serviços de estimativa de estoque de carbono.</li>
              <li>Melhoria contínua dos algoritmos e metodologias da plataforma, de forma anonimizada.</li>
              <li>Envio de comunicações sobre oportunidades no mercado voluntário de carbono, quando consentido.</li>
              <li>Composição de banco de dados de fornecedores e compradores de créditos de carbono, quando consentido.</li>
              <li>Elaboração de estudos científicos agregados sobre potencial de geração de créditos no Brasil, quando consentido.</li>
            </ul>
          </section>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              4. Base Legal (Lei 13.709/2018 — LGPD)
            </h3>
            <p>
              O tratamento dos dados pessoais realizado por esta plataforma fundamenta-se
              no <strong style={{ color: C.textoClaro }}>Art. 7º, inciso I</strong> (consentimento livre, informado e inequívoco do titular) e no
              <strong style={{ color: C.textoClaro }}> inciso IV</strong> (execução de contrato ou de procedimentos preliminares relacionados a contrato do qual seja parte o titular).
              Consentimentos adicionais são independentes e podem ser revogados a qualquer tempo.
            </p>
          </section>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              5. Medidas de Segurança
            </h3>
            <p>
              Os dados são armazenados com criptografia <strong style={{ color: C.textoClaro }}>AES-256</strong> em repouso
              e transmitidos exclusivamente via <strong style={{ color: C.textoClaro }}>HTTPS/TLS</strong>.
              Senhas são armazenadas apenas em formato de hash bcrypt — a Meridiano Tecnologia
              nunca tem acesso à senha em texto simples. O acesso à base de dados é restrito
              a colaboradores com necessidade operacional comprovada.
            </p>
          </section>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              6. Direitos do Titular (Art. 18 — LGPD)
            </h3>
            <p className="mb-2">O titular tem direito a, a qualquer momento:</p>
            <ul className="list-disc pl-4 space-y-1">
              <li>Confirmar a existência de tratamento e acessar seus dados.</li>
              <li>Corrigir dados incompletos, inexatos ou desatualizados.</li>
              <li>Solicitar anonimização, bloqueio ou eliminação de dados desnecessários.</li>
              <li>Portabilidade dos dados a outro fornecedor de serviço.</li>
              <li>Revogar o consentimento a qualquer tempo, sem prejuízo da licitude do tratamento anterior.</li>
              <li>Peticionar perante a Autoridade Nacional de Proteção de Dados (ANPD).</li>
            </ul>
          </section>

          <section>
            <h3 className="font-bold mb-2 text-sm" style={{ color: C.textoClaro }}>
              7. Contato
            </h3>
            <p>
              Para exercer seus direitos ou esclarecer dúvidas sobre o tratamento de dados, entre em contato
              com nosso Encarregado de Proteção de Dados (DPO):{' '}
              <a href="mailto:privacidade@meridianotecnologia.com.br" style={{ color: C.verde }}>
                privacidade@meridianotecnologia.com.br
              </a>
            </p>
          </section>

        </div>

        {/* Rodapé do modal */}
        <div
          className="px-6 py-4 flex-shrink-0"
          style={{ borderTop: `1px solid ${C.borda}` }}
        >
          <button
            type="button"
            onClick={onFechar}
            className="w-full py-3 rounded-xl font-semibold text-sm transition-all hover:opacity-90"
            style={{ background: C.verde, color: '#fff' }}
          >
            Entendi e fechei
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function PaginaCadastro() {
  const navegar = useNavigate()

  // Campos do formulário
  const [nome, setNome]                       = useState('')
  const [email, setEmail]                     = useState('')
  const [telefone, setTelefone]               = useState('')
  const [senha, setSenha]                     = useState('')
  const [confirmacao, setConfirmacao]         = useState('')
  const [mostrarSenha, setMostrarSenha]       = useState(false)
  const [mostrarConfirm, setMostrarConfirm]   = useState(false)

  // Consentimentos
  const [marcados, setMarcados] = useState({
    termos:            false,
    dados_tecnicos:    false,
    banco_fornecedores: false,
    comprador:         false,
    uniao_areas:       false,
    estudo_cientifico: false,
  })

  // Estado de UI
  const [modalAberto, setModalAberto] = useState(false)
  const [carregando, setCarregando]   = useState(false)
  const [mensagemErro, setMensagemErro] = useState('')

  const alternarMarcado = (id) =>
    setMarcados((prev) => ({ ...prev, [id]: !prev[id] }))

  // Validações derivadas
  const requisitoseSenha = {
    tamanho:   senha.length >= 8,
    maiuscula: /[A-Z]/.test(senha),
    minuscula: /[a-z]/.test(senha),
    numero:    /\d/.test(senha),
  }
  const senhaValida      = Object.values(requisitoseSenha).every(Boolean)
  const senhasIguais     = senha === confirmacao && confirmacao !== ''
  const obrigatoriosMarcados = marcados.termos && marcados.dados_tecnicos
  const podeSubmeter     = obrigatoriosMarcados && senhaValida && senhasIguais && nome && email && !carregando

  const formatarTelefone = (v) => {
    const digitos = v.replace(/\D/g, '').slice(0, 11)
    if (digitos.length <= 2) return digitos
    if (digitos.length <= 7) return `(${digitos.slice(0, 2)}) ${digitos.slice(2)}`
    return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`
  }

  const handleSubmeter = async (e) => {
    e.preventDefault()
    setMensagemErro('')

    if (!senhaValida) {
      setMensagemErro('A senha não atende a todos os requisitos.')
      return
    }
    if (!senhasIguais) {
      setMensagemErro('As senhas não coincidem.')
      return
    }

    setCarregando(true)
    try {
      await api.post('/usuarios/cadastrar', {
        nome,
        email,
        senha,
        ...(telefone ? { telefone: telefone.replace(/\D/g, '') } : {}),
      })

      const respLogin = await api.post('/auth/login', { email, senha })
      localStorage.setItem('carbono_token', respLogin.data.token_acesso)

      navegar('/painel')
    } catch (err) {
      const detalhe = err.response?.data?.detail
      setMensagemErro(
        typeof detalhe === 'string'
          ? detalhe
          : 'Não foi possível criar a conta. Verifique os dados e tente novamente.'
      )
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div
      className="min-h-screen"
      style={{ fontFamily: "'DM Sans', sans-serif", background: C.fundoEscuro }}
    >
      <NavbarCadastro />

      {modalAberto && <ModalPolitica onFechar={() => setModalAberto(false)} />}

      <div className="flex items-start justify-center px-4 pt-28 pb-16">
        <div className="w-full max-w-xl">

          {/* Cabeçalho */}
          <div className="text-center mb-8">
            <span
              className="inline-block text-xs font-semibold uppercase tracking-widest px-4 py-1.5 rounded-full mb-4"
              style={{ background: C.fundoCard, color: C.verde, border: `1px solid ${C.borda}` }}
            >
              Conta gratuita
            </span>
            <h1
              className="text-3xl sm:text-4xl font-bold mb-2"
              style={{ color: C.textoClaro, letterSpacing: '-0.02em' }}
            >
              Crie sua conta
            </h1>
            <p className="text-sm" style={{ color: C.textoMuted }}>
              Acesse a análise detalhada da sua propriedade e o mercado de carbono.
            </p>
          </div>

          <form onSubmit={handleSubmeter} noValidate>
            {/* ── Dados pessoais ── */}
            <div
              className="rounded-2xl p-6 mb-4"
              style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
            >
              <h2 className="text-sm font-bold mb-4 uppercase tracking-widest" style={{ color: C.textoMuted }}>
                Dados pessoais
              </h2>

              <CampoTexto
                rotulo="Nome completo"
                valor={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Seu nome completo"
              />

              <CampoTexto
                rotulo="E-mail"
                tipo="email"
                valor={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com.br"
              />

              <CampoTexto
                rotulo="Telefone"
                tipo="tel"
                valor={telefone}
                onChange={(e) => setTelefone(formatarTelefone(e.target.value))}
                placeholder="(11) 99999-9999"
                obrigatorio={false}
              />

              {/* Senha */}
              <div className="mb-4">
                <label className="block text-sm font-semibold mb-1.5" style={{ color: C.textoClaro }}>
                  Senha
                </label>
                <div className="relative">
                  <input
                    type={mostrarSenha ? 'text' : 'password'}
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
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
                  <button
                    type="button"
                    onClick={() => setMostrarSenha((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold"
                    style={{ color: C.textoMuted, background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    {mostrarSenha ? 'Ocultar' : 'Mostrar'}
                  </button>
                </div>
                <RequisitoseSenha senha={senha} />
              </div>

              {/* Confirmação de senha */}
              <div className="mb-0">
                <label className="block text-sm font-semibold mb-1.5" style={{ color: C.textoClaro }}>
                  Confirme a senha
                </label>
                <div className="relative">
                  <input
                    type={mostrarConfirm ? 'text' : 'password'}
                    value={confirmacao}
                    onChange={(e) => setConfirmacao(e.target.value)}
                    placeholder="Repita a senha"
                    required
                    className="w-full rounded-xl px-4 py-3 text-sm outline-none"
                    style={{
                      background: C.inputBg,
                      color: C.textoClaro,
                      border: `1px solid ${
                        confirmacao && !senhasIguais ? C.erro : C.bordaInput
                      }`,
                      paddingRight: '80px',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarConfirm((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold"
                    style={{ color: C.textoMuted, background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    {mostrarConfirm ? 'Ocultar' : 'Mostrar'}
                  </button>
                </div>
                {confirmacao && !senhasIguais && (
                  <p className="text-xs mt-1.5" style={{ color: C.erro }}>
                    As senhas não coincidem.
                  </p>
                )}
                {confirmacao && senhasIguais && (
                  <p className="text-xs mt-1.5" style={{ color: C.verde }}>
                    ✓ Senhas conferem.
                  </p>
                )}
              </div>
            </div>

            {/* ── Consentimentos ── */}
            <div
              className="rounded-2xl p-6 mb-4"
              style={{ background: C.fundoCard, border: `1px solid ${C.borda}` }}
            >
              <h2 className="text-sm font-bold mb-1 uppercase tracking-widest" style={{ color: C.textoMuted }}>
                Consentimentos e preferências
              </h2>
              <p className="text-xs mb-5" style={{ color: C.textoMuted }}>
                Os dois primeiros são obrigatórios para uso da plataforma. Os demais são opcionais e podem ser alterados a qualquer momento no painel.
              </p>

              {/* Obrigatórios */}
              <div className="space-y-2 mb-5">
                {CONSENTIMENTOS.filter((c) => c.obrigatorio).map((c) => (
                  <ItemConsentimento
                    key={c.id}
                    consentimento={c}
                    marcado={marcados[c.id]}
                    onChange={() => alternarMarcado(c.id)}
                    onAbrirModal={() => setModalAberto(true)}
                  />
                ))}
              </div>

              {/* Separador */}
              <div
                className="flex items-center gap-3 mb-5"
                style={{ borderTop: `1px solid ${C.borda}` }}
              >
                <span
                  className="text-xs font-semibold uppercase tracking-widest mt-4 whitespace-nowrap"
                  style={{ color: C.textoMuted }}
                >
                  Opcionais
                </span>
              </div>

              {/* Opcionais */}
              <div className="space-y-2">
                {CONSENTIMENTOS.filter((c) => !c.obrigatorio).map((c) => (
                  <ItemConsentimento
                    key={c.id}
                    consentimento={c}
                    marcado={marcados[c.id]}
                    onChange={() => alternarMarcado(c.id)}
                    onAbrirModal={null}
                  />
                ))}
              </div>
            </div>

            {/* ── Mensagem de erro ── */}
            {mensagemErro && (
              <div
                className="rounded-xl px-4 py-3 mb-4 text-sm"
                style={{ background: C.erroFundo, color: C.erro, border: `1px solid #5c1a1a` }}
              >
                {mensagemErro}
              </div>
            )}

            {/* ── Botão de cadastro ── */}
            <button
              type="submit"
              disabled={!podeSubmeter}
              className="w-full py-4 rounded-xl font-bold text-sm transition-all"
              style={{
                background: podeSubmeter ? C.verde : C.inputBg,
                color: podeSubmeter ? '#fff' : C.textoMuted,
                cursor: podeSubmeter ? 'pointer' : 'not-allowed',
                border: `1px solid ${podeSubmeter ? C.verde : C.borda}`,
              }}
            >
              {carregando ? 'Criando conta…' : 'Criar conta gratuitamente →'}
            </button>

            {!obrigatoriosMarcados && (
              <p className="text-xs text-center mt-2" style={{ color: C.textoMuted }}>
                Marque os dois consentimentos obrigatórios para continuar.
              </p>
            )}

            <p className="text-xs text-center mt-4" style={{ color: C.textoMuted }}>
              Ao criar sua conta, você confirma ter lido a{' '}
              <button
                type="button"
                onClick={() => setModalAberto(true)}
                className="underline"
                style={{ color: C.verde, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              >
                Política de privacidade
              </button>
              .
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
