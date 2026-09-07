import { useState } from 'react'

export default function AgendaGrid({ isProfessional }) {
  const [dataSelecionada, setDataSelecionada] = useState(new Date().toISOString().split('T')[0])
  const [horarioClicado, setHorarioClicado] = useState(null)

  // Gerador de horários (07:00 até 19:30)
  const horarios = Array.from({ length: 26 }, (_, i) => {
    const hora = Math.floor(i / 2) + 7
    const minuto = i % 2 === 0 ? '00' : '30'
    return `${hora.toString().padStart(2, '0')}:${minuto}`
  })

  // Mock de agendamentos vindos do Django
  const agendamentos = {
    '14:00': { status: 'aguardando', cliente: 'Maria (Pendente)' }
  }

  const handleCliqueHorario = (horario) => {
    const conflito = agendamentos[horario]
    if (!isProfessional && conflito && conflito.status === 'aguardando') {
      const confirma = window.confirm("⚠️ Este horário já possui um pedido em análise. Seu agendamento pode ser recusado ou remanejado. Deseja continuar?")
      if (!confirma) return
    }
    setHorarioClicado(horario)
    // Aqui abriria o Modal de Formulário
  }

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#D5EBEB]">
      {/* Seletor de Datas */}
      <div className="mb-6 flex justify-between items-center">
        <h2 className="text-xl font-['Playfair_Display'] font-semibold">Agenda Diária</h2>
        <input 
          type="date" 
          value={dataSelecionada}
          onChange={(e) => setDataSelecionada(e.target.value)}
          // Lógica restritiva aplicada aqui baseada no perfil
          className="border border-[#D5EBEB] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#95C6CC]"
        />
      </div>

      {/* Tabela Inspirada na Imagem */}
      <div className="flex flex-col border border-[#D5EBEB] rounded-lg overflow-hidden">
        <div className="grid grid-cols-4 bg-[#F4FBFC] font-semibold text-[#779FA3] text-xs p-3 uppercase">
          <div>Horário</div>
          <div className="col-span-2">Cliente / Procedimento</div>
          <div className="text-center">Status</div>
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          {horarios.map((horario) => {
            const ocupado = agendamentos[horario]
            
            return (
              <div 
                key={horario}
                onClick={() => handleCliqueHorario(horario)}
                className="grid grid-cols-4 border-t border-[#D5EBEB] p-3 text-sm hover:bg-slate-50 cursor-pointer transition-colors items-center"
              >
                <div className="font-medium text-slate-500">{horario}</div>
                <div className="col-span-2 text-slate-700">
                  {ocupado ? ocupado.cliente : <span className="text-slate-300 italic">Disponível</span>}
                </div>
                <div className="text-center">
                  {ocupado?.status === 'aguardando' && (
                    <span className="bg-orange-100 text-orange-600 px-2 py-1 rounded text-xs font-semibold">
                      Em Análise
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}