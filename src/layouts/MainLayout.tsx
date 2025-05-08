import { useState } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { FiHome, FiMessageSquare, FiFile, FiDatabase, FiSettings, FiMenu, FiX, FiLogOut, FiAlertCircle } from 'react-icons/fi'

import { clearApiKey } from '@/lib/api'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  apiAvailable: boolean
  isAuthenticated: boolean
}

const MainLayout = ({ apiAvailable, isAuthenticated }: MainLayoutProps) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  
  // Navigasyon öğeleri
  const navItems = [
    { path: '/', label: 'Dashboard', icon: FiHome },
    { path: '/chat', label: 'Chat', icon: FiMessageSquare },
    { path: '/documents', label: 'Belgeler', icon: FiFile },
    { path: '/data-sources', label: 'Veri Kaynakları', icon: FiDatabase },
    { path: '/settings', label: 'Ayarlar', icon: FiSettings }
  ]
  
  // Çıkış yap
  const handleLogout = () => {
    clearApiKey()
    navigate('/login')
  }
  
  // Güncel yol kontrolü
  const isActive = (path: string) => location.pathname === path
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobil Sidebar Toggle */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 bg-white border-b shadow-sm">
        <div className="flex justify-between items-center px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.svg" alt="ModularMind" className="h-8 w-8" />
            <span className="font-bold text-gray-900">ModularMind</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
          >
            {sidebarOpen ? <FiX size={24} /> : <FiMenu size={24} />}
          </button>
        </div>
      </div>
      
      {/* Sidebar */}
      <div className={cn(
        "fixed top-0 left-0 h-full w-64 bg-white border-r z-20 transition-transform duration-300 transform",
        sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="p-4 border-b">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.svg" alt="ModularMind" className="h-8 w-8" />
            <span className="font-bold text-gray-900">ModularMind</span>
          </Link>
        </div>
        
        <div className="p-4">
          <nav className="space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center px-3 py-2 rounded-lg text-sm font-medium",
                  isActive(item.path)
                    ? "bg-primary-50 text-primary-700"
                    : "text-gray-700 hover:bg-gray-100"
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className={cn(
                  "mr-3 h-5 w-5",
                  isActive(item.path) ? "text-primary-700" : "text-gray-500"
                )} />
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t">
          <button
            onClick={handleLogout}
            className="flex items-center w-full px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <FiLogOut className="mr-3 h-5 w-5 text-gray-500" />
            Çıkış Yap
          </button>
        </div>
      </div>
      
      {/* Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-10 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}
      
      {/* Ana İçerik */}
      <div className="lg:pl-64 pt-0 lg:pt-0">
        <div className="p-4 pt-16 lg:pt-4">
          {!apiAvailable && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <FiAlertCircle className="h-5 w-5 text-red-500" />
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium">API Bağlantı Hatası</h3>
                  <div className="mt-1 text-sm">
                    <p>
                      API sunucusuna bağlanılamıyor. Lütfen sunucunun çalıştığından emin olun.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <Outlet />
        </div>
      </div>
    </div>
  )
}

export default MainLayout