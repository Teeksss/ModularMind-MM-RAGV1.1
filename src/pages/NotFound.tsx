import { Link } from 'react-router-dom'
import { FiAlertTriangle } from 'react-icons/fi'

const NotFound = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <FiAlertTriangle size={64} className="text-primary-600" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          404 - Sayfa Bulunamadı
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Aradığınız sayfa mevcut değil veya taşınmış olabilir.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="flex flex-col space-y-4">
            <p className="text-center text-gray-700">
              Ana sayfaya dönmek veya giriş yapmak için aşağıdaki bağlantıları kullanabilirsiniz.
            </p>
            <div className="flex space-x-4">
              <Link
                to="/"
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Ana Sayfa
              </Link>
              <Link
                to="/login"
                className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Giriş Yap
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotFound