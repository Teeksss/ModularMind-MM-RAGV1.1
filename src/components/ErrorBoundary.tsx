import React, { Component, ErrorInfo, ReactNode } from 'react'
import { FiAlertTriangle, FiRefreshCw } from 'react-icons/fi'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({
      error,
      errorInfo
    })
    
    // Opsiyonel: Hata takip sistemi entegrasyonu
    console.error('Uygulama hatası:', error, errorInfo)
  }
  
  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Özel hata bileşeni
      if (this.props.fallback) {
        return this.props.fallback
      }
      
      // Varsayılan hata bileşeni
      return (
        <div className="min-h-[300px] flex flex-col items-center justify-center p-6 rounded-lg border border-red-200 bg-red-50 text-red-800">
          <FiAlertTriangle size={48} className="text-red-500 mb-4" />
          <h2 className="text-lg font-semibold mb-2">Bir Hata Oluştu</h2>
          <p className="text-sm text-center mb-4 max-w-md">
            Uygulama beklenmeyen bir hata ile karşılaştı. Lütfen sayfayı yenileyin veya tekrar deneyin.
          </p>
          {process.env.NODE_ENV === 'development' && (
            <div className="text-xs text-left w-full max-w-lg p-3 bg-red-100 rounded overflow-auto my-2">
              <p className="font-bold mb-1">{this.state.error?.toString()}</p>
              <pre className="whitespace-pre-wrap">
                {this.state.errorInfo?.componentStack}
              </pre>
            </div>
          )}
          <button
            onClick={this.handleReset}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg flex items-center hover:bg-red-700"
          >
            <FiRefreshCw className="mr-2" />
            Yeniden Dene
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary