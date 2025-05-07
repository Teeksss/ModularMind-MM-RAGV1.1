import React from 'react';
import { FaCircleNotch } from 'react-icons/fa';

interface LoadingOverlayProps {
  isLoading: boolean;
  message?: string;
  children: React.ReactNode;
  spinnerSize?: number;
  bgOpacity?: 'light' | 'medium' | 'dark';
  fullscreen?: boolean;
}

const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isLoading,
  message = 'Loading...',
  children,
  spinnerSize = 32,
  bgOpacity = 'medium',
  fullscreen = false
}) => {
  if (!isLoading) return <>{children}</>;
  
  // Determine background opacity class
  let bgClass = 'bg-white/50 dark:bg-gray-900/50'; // medium (default)
  if (bgOpacity === 'light') bgClass = 'bg-white/30 dark:bg-gray-900/30';
  if (bgOpacity === 'dark') bgClass = 'bg-white/70 dark:bg-gray-900/70';
  
  // Determine positioning classes
  const positionClass = fullscreen 
    ? 'fixed inset-0 z-50'
    : 'absolute inset-0 z-10';
  
  return (
    <div className="relative">
      {children}
      
      <div className={`${positionClass} flex flex-col items-center justify-center ${bgClass} backdrop-blur-sm transition-opacity duration-300`}>
        <div className="flex flex-col items-center bg-white/70 dark:bg-gray-800/70 backdrop-blur-md p-6 rounded-lg shadow-lg">
          <FaCircleNotch 
            className="animate-spin text-blue-600 dark:text-blue-400 mb-3"
            size={spinnerSize}
          />
          
          {message && (
            <p className="text-gray-800 dark:text-gray-200 font-medium text-center">
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoadingOverlay;