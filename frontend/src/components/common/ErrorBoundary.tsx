import React, { Component, ErrorInfo, ReactNode } from 'react';
import { FiAlertTriangle } from 'react-icons/fi';
import Button from './Button';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  resetError = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-6 max-w-xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md mt-8 border border-red-200 dark:border-red-800">
          <div className="flex items-center text-red-500 mb-4">
            <FiAlertTriangle size={24} className="mr-2" />
            <h2 className="text-xl font-semibold">Bir hata oluştu</h2>
          </div>
          
          <div className="text-gray-700 dark:text-gray-300 mb-4">
            <p className="mb-2">Uygulama beklenmeyen bir hata ile karşılaştı.</p>
            <div className="bg-gray-100 dark:bg-gray-900 p-3 rounded text-sm font-mono overflow-auto max-h-40">
              {this.state.error?.message || 'Bilinmeyen hata'}
            </div>
          </div>
          
          <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-2">
            <Button 
              onClick={this.resetError} 
              variant="primary"
            >
              Tekrar Dene
            </Button>
            <Button 
              onClick={() => window.location.href = '/'}
              variant="secondary"
            >
              Ana Sayfaya Dön
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;