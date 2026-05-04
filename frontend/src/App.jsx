import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PaginaInicial from './pages/PaginaInicial'
import PaginaLogin from './pages/PaginaLogin'
import PaginaCadastro from './pages/PaginaCadastro'
import PaginaEstimativa from './pages/PaginaEstimativa'
import PaginaResultado from './pages/PaginaResultado'
import PaginaPainel from './pages/PaginaPainel'

function RotaProtegida({ children }) {
  const token = localStorage.getItem('carbono_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PaginaInicial />} />
        <Route path="/login" element={<PaginaLogin />} />
        <Route path="/cadastro" element={<PaginaCadastro />} />
        <Route path="/estimativa" element={<PaginaEstimativa />} />
        <Route path="/resultado/:analise_id" element={<PaginaResultado />} />
        <Route
          path="/painel"
          element={
            <RotaProtegida>
              <PaginaPainel />
            </RotaProtegida>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
