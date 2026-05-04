import { useParams } from 'react-router-dom'

export default function PaginaResultado() {
  const { analise_id } = useParams()

  return (
    <main className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold">Resultado</h1>
      <p className="mt-2 text-gray-500">Análise: {analise_id}</p>
    </main>
  )
}
