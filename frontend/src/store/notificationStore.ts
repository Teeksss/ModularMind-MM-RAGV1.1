import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface NotificationAction {
  label: string;
  onClick: () => void;
  closeOnClick?: boolean;
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number; // in milliseconds, undefined for no auto-dismiss
  createdAt: Date;
  actions?: NotificationAction[];
}

interface NotificationStore {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => string;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  updateNotification: (id: string, updates: Partial<Omit<Notification, 'id' | 'createdAt'>>) => void;
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  
  addNotification: (notification) => {
    const id = uuidv4();
    
    // Set default duration based on type if not specified
    let duration = notification.duration;
    if (duration === undefined) {
      // Default durations by type
      switch (notification.type) {
        case 'success':
          duration = 5000; // 5 seconds
          break;
        case 'info':
          duration = 7000; // 7 seconds
          break;
        case 'warning':
          duration = 10000; // 10 seconds
          break;
        case 'error':
          duration = 0; // No auto-dismiss for errors
          break;
        default:
          duration = 7000; // 7 seconds default
      }
    }
    
    // Create the notification
    const newNotification: Notification = {
      id,
      createdAt: new Date(),
      ...notification,
      duration,
    };
    
    // Add the notification
    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));
    
    // Auto-remove the notification after duration if set
    if (duration > 0) {
      setTimeout(() => {
        get().removeNotification(id);
      }, duration);
    }
    
    // Return the ID for reference
    return id;
  },
  
  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter(
        (notification) => notification.id !== id
      ),
    }));
  },
  
  clearNotifications: () => {
    set({ notifications: [] });
  },
  
  updateNotification: (id, updates) => {
    set((state) => ({
      notifications: state.notifications.map((notification) => 
        notification.id === id
          ? { ...notification, ...updates }
          : notification
      ),
    }));
  },
}));