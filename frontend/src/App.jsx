import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard' // (Se ainda não criou o Dashboard, pode ignorar essa linha por enquanto ou criar um arquivo vazio para ele)

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Rota raiz (Tela de Login) */}
        <Route path="/" element={<Login />} />
        
        {/* Rota do Painel */}
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}