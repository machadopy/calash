
import { useState } from 'react'
import api from '../services/api'
import Layout from '../components/Layout'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await api.post('/auth/token/', {
        email: email,
        password: password
      })

      const { access, refresh } = response.data
      localStorage.setItem('accessToken', access)
      localStorage.setItem('refreshToken', refresh)

      alert("Login realizado com sucesso! 🎉")
    } catch (err) {
      console.error(err)
      setError("Falha no login. Verifique suas credenciais.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Calash" subtitle="Acesse o painel para gerenciar o sistema">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-xs p-3 rounded-xl mb-4 text-center font-medium">
          {error}
        </div>
      )}

      <form onSubmit={handleLogin} className="space-y-4">
        <div className="mb-4">
          <label className="block text-[11px] font-medium text-[#667777] mb-2 uppercase tracking-[0.5px]">
            E-mail
          </label>
          <input 
            type="email" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-[12px_16px] border-[1.5px] border-[#D5EBEB] rounded-[12px] text-sm text-[#2C2C2C] bg-white outline-none focus:border-[#95C6CC] focus:ring-4 focus:ring-[#95C6CC]/25 transition-all"
            placeholder="seu@email.com"
            required
          />
        </div>
        
        <div className="mb-4">
          <label className="block text-[11px] font-medium text-[#667777] mb-2 uppercase tracking-[0.5px]">
            Senha
          </label>
          <input 
            type="password" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-[12px_16px] border-[1.5px] border-[#D5EBEB] rounded-[12px] text-sm text-[#2C2C2C] bg-white outline-none focus:border-[#95C6CC] focus:ring-4 focus:ring-[#95C6CC]/25 transition-all"
            placeholder="••••••••"
            required
          />
        </div>

        <button 
          type="submit" 
          disabled={loading}
          className="w-full bg-[#95C6CC] hover:bg-[#779FA3] text-white border-none p-[14px] rounded-[12px] text-sm font-semibold cursor-pointer transition-all shadow-[0_4px_15px_rgba(149,198,204,0.3)] uppercase tracking-[0.5px] mt-2 disabled:opacity-70"
        >
          {loading ? "Autenticando..." : "Entrar"}
        </button>
      </form>

      <div className="text-center mt-5 text-[11px] text-[#889999]">
        Sistema integrado com API Django &bull; Calash
      </div>
    </Layout>
  )
}