import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm, FormProvider } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { FaUser, FaLock, FaSignInAlt, FaSpinner } from 'react-icons/fa';

import { useAuthStore } from '../../store/authStore';
import { useNotificationStore } from '../../store/notificationStore';
import FormField from '../../components/common/FormField';

interface LoginFormData {
  username: string;
  password: string;
  rememberMe: boolean;
}

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();
  const { addNotification } = useNotificationStore();

  // Form validation schema
  const validationSchema = yup.object().shape({
    username: yup
      .string()
      .required(t('validation.required', { field: t('auth.username') }))
      .min(3, t('validation.minLength', { field: t('auth.username'), length: 3 })),
    password: yup
      .string()
      .required(t('validation.required', { field: t('auth.password') }))
      .min(6, t('validation.minLength', { field: t('auth.password'), length: 6 })),
    rememberMe: yup.boolean(),
  });

  // Form methods
  const formMethods = useForm<LoginFormData>({
    resolver: yupResolver(validationSchema),
    defaultValues: {
      username: '',
      password: '',
      rememberMe: false,
    },
  });
  
  const { handleSubmit, register, watch, formState: { errors } } = formMethods;

  // Handle form submission
  const onSubmit = async (data: LoginFormData) => {
    clearError();
    
    try {
      // Attempt login
      await login(data.username, data.password, data.rememberMe);
      
      // Show success notification
      addNotification({
        type: 'success',
        title: t('auth.welcomeBack'),
        message: t('auth.loginSuccessful'),
      });
      
      // Navigate to dashboard
      navigate('/dashboard');
      
    } catch (err: any) {
      // Error is handled by auth store and displayed below
      console.error('Login failed:', err);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full p-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('auth.signIn')}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            {t('auth.signInToContinue')}
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-md">
            {error}
          </div>
        )}

        <FormProvider {...formMethods}>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Username field */}
            <FormField
              name="username"
              label={t('auth.username')}
              placeholder={t('auth.enterUsername')}
              required
              icon={<FaUser className="text-gray-400" />}
              autoComplete="username"
            />

            {/* Password field */}
            <FormField
              name="password"
              label={t('auth.password')}
              type="password"
              placeholder={t('auth.enterPassword')}
              required
              icon={<FaLock className="text-gray-400" />}
              autoComplete="current-password"
            />

            {/* Remember me checkbox */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="rememberMe"
                  type="checkbox"
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                  {...register('rememberMe')}
                />
                <label htmlFor="rememberMe" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  {t('auth.rememberMe')}
                </label>
              </div>
              <div className="text-sm">
                <Link to="/auth/forgot-password" className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
                  {t('auth.forgotPassword')}
                </Link>
              </div>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <FaSpinner className="animate-spin mr-2" />
                  {t('auth.signingIn')}
                </>
              ) : (
                <>
                  <FaSignInAlt className="mr-2" />
                  {t('auth.signIn')}
                </>
              )}
            </button>

            {/* Sign up link */}
            <div className="text-center mt-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t('auth.dontHaveAccount')}{' '}
                <Link to="/auth/register" className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium">
                  {t('auth.signUp')}
                </Link>
              </p>
            </div>
          </form>
        </FormProvider>
      </div>
    </div>
  );
};

export default LoginPage;