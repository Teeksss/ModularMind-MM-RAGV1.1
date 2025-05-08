import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FiAlertCircle, FiCheckCircle } from 'react-icons/fi'

const Register = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    organization: ''
  })
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    setLoading(true)
    setError(null)
    
    try {
      // API kaydını simüle et
      // Gerçek implementasyonda burada API'ye kayıt isteği gönderilebilir
      setTimeout(() => {
        setSuccess(true)
        setLoading(false)
      }, 1500)
    } catch (err) {
      setError('Kayıt işlemi sırasında bir hata oluştu')
      setLoading(false)
    }
  }
  
  if (success) {
    return (
      <div className="text-center">
        <div className="flex justify-center mb-2">
          <FiCheckCircle className="h-10 w-10 text-green-500" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Kayıt Talebiniz Alındı
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          API anahtarınız onaylandıktan sonra e-posta adresinize gönderilecektir.
        </p>
        <Link
          to="/login"
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          Giriş Sayfasına Dön
        </Link>
      </div>
    )
  }
  
  return (
    <div>
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        API Erişimi İste
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
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
            Ad Soyad
          </label>
          <div className="mt-1">
            <input
              id="name"
              name="name"
              type="text"
              required
              value={formData.name}
              onChange={handleChange}
              className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            E-posta Adresi
          </label>
          <div className="mt-1">
            <input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="organization" className="block text-sm font-medium text-gray-700">
            Kurum / Organizasyon
          </label>
          <div className="mt-1">
            <input
              id="organization"
              name="organization"
              type="text"
              value={formData.organization}
              onChange={handleChange}
              className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>
        </div>
        
        <div>
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-primary-400 disabled:cursor-not-allowed"
          >
            {loading ? 'İşleniyor...' : 'Erişim Talep Et'}
          </button>
        </div>
      </form>
      
      <div className="mt-6">
        <p className="text-center text-sm text-gray-600">
          Zaten bir API anahtarınız var mı?{' '}
          <Link to="/login" className="font-medium text-primary-600 hover:text-primary-500">
            Giriş Yapın
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Register