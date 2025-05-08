import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { FiAlertCircle } from 'react-icons/fi'

import { setApiKey } from '@/lib/api'

interface LoginProps {
  setAuth: (value: boolean) => void
}

const Login = ({ setAuth }: LoginProps) => {
  const [apiKey, setApiKeyInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!apiKey.trim()) {
      setError('API anahtarı gereklidir')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      // API anahtarını kaydet
      setApiKey(apiKey)
      
      // API'yi test et
      // Actual API test would go here, but for demo purposes we'll just set auth
      setAuth(true)
      navigate('/')
    } catch (err) {
      setApiKey('')
      setError('Geçersiz API anahtarı')
      setLoading(false)
    }
  }
  
  return (
    <div>
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Giriş Yap
      </h3>
      
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <div className="flex">
            <div className="flex-shrink-0">
              <FiAlertCircle className="h-5 w-5 text-red-500" />
            </div>
            <div className="ml-3">
              <p className="text-sm">{error}</p>
            </div>
          </div>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="api-key" className="block text-sm font-medium text-gray-700">
            API Anahtarı
          </label>
          <div className="mt-1">
            <input
              id="api-key"
              name="api-key"
              type="password"
              autoComplete="current-password"
              required
              value={apiKey}
              onChange={(e) => setApiKeyInput(e.target.value)}
              className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder="API anahtarınızı girin"
            />
          </div>
        </div>
        
        <div>
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-primary-400"
          >
            {loading ? 'Giriş Yapılıyor...' : 'Giriş Yap'}
          </button>
        </div>
      </form>
      
      <div className="mt-6">
        <p className="text-center text-sm text-gray-600">
          Henüz API anahtarınız yok mu?{' '}
          <Link to="/register" className="font-medium text-primary-600 hover:text-primary-500">
            Kayıt Olun
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Login