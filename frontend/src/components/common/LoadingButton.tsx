import React from 'react';
import { FaCircleNotch } from 'react-icons/fa';

interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading: boolean;
  loadingText?: string;
  spinnerSize?: number;
  spinnerPosition?: 'left' | 'right';
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info' | 'light' | 'dark';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const LoadingButton: React.FC<LoadingButtonProps> = ({
  children,
  isLoading,
  loadingText,
  spinnerSize = 16,
  spinnerPosition = 'left',
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  icon,
  iconPosition = 'left',
  className,
  disabled,
  ...rest
}) => {
  // Determine variant classes
  const getVariantClass = () => {
    switch (variant) {
      case 'primary':
        return 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500 text-white';
      case 'secondary':
        return 'bg-gray-600 hover:bg-gray-700 focus:ring-gray-500 text-white';
      case 'success':
        return 'bg-green-600 hover:bg-green-700 focus:ring-green-500 text-white';
      case 'danger':
        return 'bg-red-600 hover:bg-red-700 focus:ring-red-500 text-white';
      case 'warning':
        return 'bg-yellow-500 hover:bg-yellow-600 focus:ring-yellow-500 text-white';
      case 'info':
        return 'bg-cyan-500 hover:bg-cyan-600 focus:ring-cyan-500 text-white';
      case 'light':
        return 'bg-gray-100 hover:bg-gray-200 focus:ring-gray-300 text-gray-800 border border-gray-300';
      case 'dark':
        return 'bg-gray-800 hover:bg-gray-900 focus:ring-gray-700 text-white';
      default:
        return 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500 text-white';
    }
  };

  // Determine size classes
  const getSizeClass = () => {
    switch (size) {
      case 'sm':
        return 'py-1 px-3 text-sm';
      case 'lg':
        return 'py-3 px-6 text-lg';
      case 'md':
      default:
        return 'py-2 px-4 text-base';
    }
  };

  // Determine width class
  const getWidthClass = () => {
    return fullWidth ? 'w-full' : '';
  };

  // Combine all classes
  const buttonClasses = `
    ${getVariantClass()}
    ${getSizeClass()}
    ${getWidthClass()}
    font-medium rounded-md shadow-sm 
    focus:outline-none focus:ring-2 focus:ring-offset-2
    transition-colors duration-200
    ${disabled || isLoading ? 'opacity-70 cursor-not-allowed' : ''}
    ${className || ''}
  `;

  // Render content based on loading state
  const renderContent = () => {
    if (isLoading) {
      return (
        <>
          {spinnerPosition === 'left' && (
            <FaCircleNotch 
              className="animate-spin mr-2" 
              size={spinnerSize} 
            />
          )}
          {loadingText || children}
          {spinnerPosition === 'right' && (
            <FaCircleNotch 
              className="animate-spin ml-2" 
              size={spinnerSize} 
            />
          )}
        </>
      );
    }

    return (
      <>
        {icon && iconPosition === 'left' && (
          <span className="mr-2">{icon}</span>
        )}
        {children}
        {icon && iconPosition === 'right' && (
          <span className="ml-2">{icon}</span>
        )}
      </>
    );
  };

  return (
    <button
      className={buttonClasses}
      disabled={disabled || isLoading}
      {...rest}
    >
      <span className="flex items-center justify-center">
        {renderContent()}
      </span>
    </button>
  );
};

export default LoadingButton;