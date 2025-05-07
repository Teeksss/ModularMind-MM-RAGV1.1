import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { FaCheckCircle, FaExclamationTriangle, FaInfoCircle, FaTimes, FaBell } from 'react-icons/fa';
import { useNotificationStore } from '../../store/notificationStore';

// Notification type icons
const NOTIFICATION_ICONS = {
  success: <FaCheckCircle className="text-green-500 dark:text-green-400" size={20} />,
  error: <FaExclamationTriangle className="text-red-500 dark:text-red-400" size={20} />,
  warning: <FaExclamationTriangle className="text-yellow-500 dark:text-yellow-400" size={20} />,
  info: <FaInfoCircle className="text-blue-500 dark:text-blue-400" size={20} />,
};

// Notification backgrounds
const NOTIFICATION_BG = {
  success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
  error: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
  warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
  info: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
};

// Progress bar colors
const PROGRESS_COLORS = {
  success: 'bg-green-500 dark:bg-green-400',
  error: 'bg-red-500 dark:bg-red-400',
  warning: 'bg-yellow-500 dark:bg-yellow-400',
  info: 'bg-blue-500 dark:bg-blue-400',
};

const NotificationSystem: React.FC = () => {
  const { t } = useTranslation();
  const { notifications, removeNotification } = useNotificationStore();
  
  // Sort notifications by creation time (most recent first)
  const sortedNotifications = [...notifications].sort(
    (a, b) => b.createdAt.getTime() - a.createdAt.getTime()
  );
  
  // Group notifications by type
  const [notificationGroups, setNotificationGroups] = useState<{
    [key: string]: typeof notifications
  }>({});
  
  // Update notification groups when notifications change
  useEffect(() => {
    const groups: { [key: string]: typeof notifications } = {};
    
    // Group similar notifications
    sortedNotifications.forEach(notification => {
      // Create a key based on title and message
      const key = `${notification.type}-${notification.title}-${notification.message}`;
      
      if (!groups[key]) {
        groups[key] = [];
      }
      
      groups[key].push(notification);
    });
    
    setNotificationGroups(groups);
  }, [sortedNotifications]);
  
  // Handle notification removal
  const handleRemove = (id: string) => {
    removeNotification(id);
  };
  
  // Handle removing all notifications in a group
  const handleRemoveGroup = (groupKey: string, notifications: typeof sortedNotifications) => {
    notifications.forEach(notification => {
      removeNotification(notification.id);
    });
  };
  
  return (
    <div className="fixed top-0 right-0 z-50 flex flex-col items-end p-4 space-y-2 max-h-screen overflow-hidden pointer-events-none">
      <AnimatePresence>
        {Object.entries(notificationGroups).map(([groupKey, groupNotifications]) => {
          // Use the first notification in the group for display
          const notification = groupNotifications[0];
          const count = groupNotifications.length;
          
          return (
            <motion.div
              key={groupKey}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 50 }}
              className="pointer-events-auto"
            >
              <div
                className={`max-w-sm w-full shadow-lg rounded-lg overflow-hidden border ${
                  NOTIFICATION_BG[notification.type]
                }`}
              >
                <div className="px-4 py-3 relative">
                  {/* Close button */}
                  <button
                    onClick={() => handleRemoveGroup(groupKey, groupNotifications)}
                    className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                    aria-label={t('common.close')}
                  >
                    <FaTimes size={16} />
                  </button>
                  
                  {/* Notification content */}
                  <div className="flex items-start">
                    <div className="flex-shrink-0 mt-0.5">
                      {NOTIFICATION_ICONS[notification.type]}
                    </div>
                    
                    <div className="ml-3 w-0 flex-1 pt-0.5 pr-8">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {notification.title}
                      </p>
                      
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                        {notification.message}
                      </p>
                      
                      {/* Show count badge if multiple notifications */}
                      {count > 1 && (
                        <div className="mt-2 flex items-center text-xs text-gray-500 dark:text-gray-400">
                          <FaBell className="mr-1" size={12} />
                          {t('notifications.count', { count })}
                        </div>
                      )}
                      
                      {/* Optional action buttons */}
                      {notification.actions && notification.actions.length > 0 && (
                        <div className="mt-3 flex space-x-2">
                          {notification.actions.map((action, index) => (
                            <button
                              key={index}
                              onClick={() => {
                                action.onClick();
                                if (action.closeOnClick) {
                                  handleRemoveGroup(groupKey, groupNotifications);
                                }
                              }}
                              className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-blue-700 bg-blue-100 hover:bg-blue-200 dark:text-blue-400 dark:bg-blue-900/40 dark:hover:bg-blue-900/60 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            >
                              {action.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Auto-dismiss progress bar */}
                  {notification.duration && notification.duration > 0 && (
                    <div className="w-full h-1 mt-2 bg-gray-200 dark:bg-gray-700 overflow-hidden">
                      <motion.div
                        className={`h-full ${PROGRESS_COLORS[notification.type]}`}
                        initial={{ width: '100%' }}
                        animate={{ width: '0%' }}
                        transition={{
                          duration: notification.duration / 1000,
                          ease: 'linear',
                        }}
                        onAnimationComplete={() => handleRemoveGroup(groupKey, groupNotifications)}
                      />
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};

export default NotificationSystem;