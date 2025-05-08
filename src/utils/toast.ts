import toast, { Toast, ToastOptions } from 'react-hot-toast';

// Base toast options
const baseOptions: ToastOptions = {
  duration: 4000,
  position: 'top-right',
};

// Success toast
export const showSuccess = (message: string, options?: ToastOptions) => {
  return toast.success(message, { ...baseOptions, ...options });
};

// Error toast
export const showError = (message: string, options?: ToastOptions) => {
  return toast.error(message, { ...baseOptions, ...options });
};

// Info toast
export const showInfo = (message: string, options?: ToastOptions) => {
  return toast(message, { ...baseOptions, ...options });
};

// Warning toast
export const showWarning = (message: string, options?: ToastOptions) => {
  return toast(message, {
    ...baseOptions,
    ...options,
    icon: '⚠️',
    style: { backgroundColor: '#fff7ed', color: '#9a3412' },
  });
};

// Loading toast
export const showLoading = (message: string, options?: ToastOptions): Toast => {
  return toast.loading(message, { ...baseOptions, ...options });
};

// Update toast
export const updateToast = (
  toastId: string, 
  message: string, 
  type: 'success' | 'error' | 'loading' | 'info' = 'info',
  options?: ToastOptions
) => {
  switch (type) {
    case 'success':
      return toast.success(message, { ...baseOptions, ...options, id: toastId });
    case 'error':
      return toast.error(message, { ...baseOptions, ...options, id: toastId });
    case 'loading':
      return toast.loading(message, { ...baseOptions, ...options, id: toastId });
    default:
      return toast(message, { ...baseOptions, ...options, id: toastId });
  }
};

// Dismiss toast
export const dismissToast = (toastId: string) => {
  toast.dismiss(toastId);
};