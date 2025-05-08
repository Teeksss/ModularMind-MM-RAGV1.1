import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotificationStore } from '@/store/notificationStore';
import { FiX, FiInfo, FiAlertCircle, FiCheckCircle, FiAlertTriangle } from 'react-icons/fi';

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

interface NotificationProps {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  autoClose?: boolean;
  duration?: number;
}

const notificationIcons = {
  info: <FiInfo className="text-blue-500" size={20} />,
  success: <FiCheckCircle className="text-green-500" size={20} />,
  warning: <FiAlertTriangle className="text-amber-500" size={20} />,
  error: <FiAlertCircle className="text-red-500" size={20} />,
};

const notificationClasses = {
  info: 'bg-blue-50 border-blue-200 dark:bg-blue-900/30 dark:border-blue-800',
  success: 'bg-green-50 border-green-200 dark:bg-green-900/30 dark:border-green-800',
  warning: 'bg-amber-50 border-amber-200 dark:bg-amber-900/30 dark:border-amber-800',
  error: 'bg-red-50 border-red-200 dark:bg-red-900/30 dark:border-red-800',
};

const Notification: React.FC<NotificationProps & { onClose: () => void }> = ({
  id,
  title,
  message,
  type = 'info',
  autoClose = true,
  duration = 5000,
  onClose,
}) => {
  useEffect(() => {
    if (autoClose) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [autoClose, duration, onClose]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={`max-w-sm w-full shadow-lg rounded-lg pointer-events-auto border ${notificationClasses[type]} overflow-hidden`}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {notificationIcons[type]}
          </div>
          <div className="ml-3 w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {title}
            </p>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              {message}
            </p>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              className="bg-transparent rounded-md inline-flex text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              onClick={onClose}
            >
              <span className="sr-only">Close</span>
              <FiX className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const NotificationSystem: React.FC = () => {
  const { notifications, removeNotification } = useNotificationStore();

  return createPortal(
    <div className="fixed inset-0 flex flex-col items-end px-4 py-6 pointer-events-none sm:p-6 z-50 space-y-4">
      <AnimatePresence>
        {notifications.map((notification) => (
          <Notification
            key={notification.id}
            {...notification}
            onClose={() => removeNotification(notification.id)}
          />
        ))}
      </AnimatePresence>
    </div>,
    document.body
  );
};

export default NotificationSystem;