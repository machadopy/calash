import Layout from '../components/Layout'
import AgendaGrid from '../components/AgendaGrid' // Faltou essa importação no seu!

export default function Dashboard() {
  return (
    <Layout title="Painel Calash" subtitle="Bem-vindo ao sistema de gestão">
      <div className="space-y-6">
        
        <p className="text-sm text-slate-600 text-center">
          Aqui você poderá ver os agendamentos e gerenciar o estúdio.
        </p>
        
        {/* Aqui estamos "injetando" a tabela na página do jeito certo */}
        <AgendaGrid isProfessional={true} />
        
        <button 
          onClick={() => {
            localStorage.clear();
            // Volta para a tela de login ao sair
            window.location.href = '/'; 
          }}
          className="w-full bg-red-500 hover:bg-red-600 active:bg-red-700 text-white p-3 rounded-xl text-sm font-semibold transition-all shadow-md"
        >
          Sair da Conta (Logout)
        </button>

      </div>
    </Layout>
  )
}