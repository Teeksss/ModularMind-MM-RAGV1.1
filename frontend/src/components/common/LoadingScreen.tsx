import React from 'react';
import { motion } from 'framer-motion';

interface LoadingScreenProps {
  text?: string;
  fullScreen?: boolean;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({
  text = 'Yükleniyor...',
  fullScreen = true,
}) => {
  const containerClasses = fullScreen
    ? 'fixed inset-0 flex items-center justify-center z-50 bg-white dark:bg-gray-900 bg-opacity-90 dark:bg-opacity-90'
    : 'flex flex-col items-center justify-center py-8';

  return (
    <div className={containerClasses}>
      <div className="flex flex-col items-center">
        <div className="relative w-24 h-24">
          <motion.div
            className="absolute inset-0 border-4 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
          <motion.div
            className="absolute inset-2 border-4 border-t-transparent border-r-transparent border-b-blue-400 border-l-transparent rounded-full"
            animate={{ rotate: -360 }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
          <motion.div
            className="absolute inset-4 border-4 border-t-transparent border-r-blue-300 border-b-transparent border-l-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        </div>
        
        {text && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 text-gray-700 dark:text-gray-300 font-medium"
          >
            {text}
          </motion.p>
        )}
      </div>
    </div>
  );
};

export default LoadingScreen;