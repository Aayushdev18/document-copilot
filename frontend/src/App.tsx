import { Navigate, Route, Routes } from "react-router-dom"

import { useAuth } from "@/lib/auth"
import { ChatPage } from "@/pages/ChatPage"
import { LoginPage } from "@/pages/LoginPage"

function PrivateRoutes() {
  const { session } = useAuth()
  if (!session) return <Navigate to="/login" replace />
  return (
    <Routes>
      <Route element={<ChatPage />}>
        <Route path="/" element={null} />
        <Route path="/c/:threadId" element={null} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={<PrivateRoutes />} />
    </Routes>
  )
}
