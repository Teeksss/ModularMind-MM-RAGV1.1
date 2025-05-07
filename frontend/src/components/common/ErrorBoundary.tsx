import React, { Component, ErrorInfo, ReactNode } from 'react';
import { FaExclamationTriangle } from 'react-icons/fa';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({
      error,
      errorInfo
    });
    
    // Call onError callback if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    // Log error to monitoring service
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
    
    // Report to error monitoring service if available
    if (window.Sentry) {
      window.Sentry.captureException(error);
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Render custom fallback UI if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4 py-12 rounded-lg">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 shadow rounded-lg p-8">
            <div className="flex justify-center">
              <FaExclamationTriangle className="h-12 w-12 text-red-500" />
            </div>
            <div className="mt-4 text-center">
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Something went wrong
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                We're sorry, but something unexpected happened.
              </p>
              {this.state.error && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900 dark:bg-opacity-20 rounded-md">
                  <p className="text-sm text-red-800 dark:text-red-300 text-left">
                    {this.state.error.toString()}
                  </p>
                </div>
              )}
              <div className="mt-6">
                <button
                  onClick={() => window.location.reload()}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Refresh page
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;