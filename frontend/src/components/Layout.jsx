export default function Layout({ children, title, subtitle }) {
  return (
    <div className="min-h-screen bg-[#F4FBFC] flex items-center justify-center p-5 font-['Poppins'] text-[#2C2C2C]">
      <div className="bg-white w-full max-w-[480px] rounded-[24px] shadow-[0_10px_30px_rgba(119,159,163,0.15)] overflow-hidden border border-[#D5EBEB]">
        
        {/* Cabeçalho Inspirado no seu HTML */}
        <div className="bg-gradient-to-br from-[#AFE9F0] to-[#95C6CC] p-[35px_20px] text-center border-b border-[#D5EBEB]">
          <h1 className="font-['Playfair_Display'] text-[26px] text-[#2C2C2C] mb-1 tracking-[1px]">
            {title || "Calash Studio"}
          </h1>
          <p className="text-[13px] text-[#4A5C5C] tracking-[0.5px]">
            {subtitle || "Painel de Gerenciamento e Atendimento"}
          </p>
        </div>

        {/* Corpo onde as telas/formulários vão entrar */}
        <div className="p-[30px_25px]">
          {children}
        </div>

      </div>
    </div>
  )
}