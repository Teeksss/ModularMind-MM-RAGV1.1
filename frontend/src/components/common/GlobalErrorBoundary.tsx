import React, { Component, ErrorInfo, ReactNode } from 'react';
import { FaExclamationTriangle, FaRedo, FaHome } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // You can log the error to an error reporting service
    console.error('Uncaught error:', error, errorInfo);
    
    // Send error to logging service (if available)
    if (window.onerror) {
      window.onerror(
        error.message,
        undefined,
        undefined,
        undefined,
        error
      );
    }
    
    this.setState({
      error,
      errorInfo
    });
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback UI
      return (
        <ErrorFallbackUI 
          error={this.state.error} 
          errorInfo={this.state.errorInfo}
          onReload={this.handleReload}
        />
      );
    }

    return this.props.children;
  }
}

interface ErrorFallbackUIProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReload: () => void;
}

const ErrorFallbackUI: React.FC<ErrorFallbackUIProps> = ({ error, errorInfo, onReload }) => {
  const navigate = useNavigate();
  
  const handleGoHome = () => {
    navigate('/');
    window.location.reload();
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 px-4">
      <div className="w-full max-w-md p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
        <div className="flex flex-col items-center text-center">
          <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full mb-4">
            <FaExclamationTriangle size={32} />
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Something went wrong
          </h1>
          
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            We're sorry, but an unexpected error has occurred. Our team has been notified.
          </p>
          
          {process.env.NODE_ENV !== 'production' && (
            <div className="w-full bg-gray-100 dark:bg-gray-700 p-4 rounded-md mb-6 overflow-auto text-left">
              <h3 className="font-mono text-sm font-bold text-red-600 dark:text-red-400 mb-2">
                {error?.toString()}
              </h3>
              
              {errorInfo && (
                <details className="font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  <summary>Stack trace</summary>
                  {errorInfo.componentStack}
                </details>
              )}
            </div>
          )}
          
          <div className="flex space-x-4">
            <button
              onClick={onReload}
              className="px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
            >
              <FaRedo className="mr-2" />
              Reload Page
            </button>
            
            <button
              onClick={handleGoHome}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
            >
              <FaHome className="mr-2" />
              Go Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GlobalErrorBoundary;