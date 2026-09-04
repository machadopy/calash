
import Layout from '../components/Layout'

export default function Dashboard() {
  return (
    <Layout title="Painel Calash" subtitle="Bem-vindo ao sistema de gestão">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Aqui você poderá ver os agendamentos e gerenciar o estúdio.
        </p>
        
        <button 
          onClick={() => {
            localStorage.clear();
            window.location.reload();
          }}
          className="w-full bg-red-500 hover:bg-red-600 text-white p-3 rounded-xl text-sm font-semibold transition-all"
        >
          Sair da Conta (Logout)
        </button>
      </div>
    </Layout>
  )
}