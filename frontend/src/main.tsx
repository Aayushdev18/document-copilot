import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import "@fontsource/fraunces/600.css"
import "@fontsource/fraunces/600-italic.css"
import App from "@/App.tsx"
import { AuthProvider } from "@/lib/auth"
import "@/index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
