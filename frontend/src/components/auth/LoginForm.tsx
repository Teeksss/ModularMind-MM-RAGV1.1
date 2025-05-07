import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BiLock, BiUser, BiEnvelope, BiLoaderAlt } from 'react-icons/bi';

import { useAuthStore } from '../../store/authStore';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Card } from '../common/Card';
import { Checkbox } from '../common/Checkbox';
import { AlertBox } from '../common/AlertBox';

const LoginForm: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, error, isLoading, clearError } = useAuthStore();
  
  const [loginData, setLoginData] = useState({
    username: '',
    password: '',
    remember_me: false
  });
  
  const [validationErrors, setValidationErrors] = useState<{
    username?: string;
    password?: string;
  }>({});
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    setLoginData(prev => ({
      ...prev,
      [name]: newValue
    }));
    
    // Clear validation errors when user types
    if (validationErrors[name as keyof typeof validationErrors]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: undefined
      }));
    }
    
    // Clear API errors when user makes changes
    if (error) {
      clearError();
    }
  };
  
  const validate = (): boolean => {
    const errors: {
      username?: string;
      password?: string;
    } = {};
    
    if (!loginData.username.trim()) {
      errors.username = t('auth.usernameRequired');
    }
    
    if (!loginData.password) {
      errors.password = t('auth.passwordRequired');
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }
    
    try {
      await login(loginData);
      navigate('/dashboard');
    } catch (error) {
      // Error is handled by the store
    }
  };
  
  return (
    <Card className="w-full max-w-md p-8">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
          {t('auth.welcomeBack')}
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          {t('auth.loginToContinue')}
        </p>
      </div>
      
      {error && (
        <AlertBox 
          type="error" 
          message={error} 
          className="mb-6" 
          onClose={clearError} 
        />
      )}
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <Input
            id="username"
            name="username"
            type="text"
            label={t('auth.usernameOrEmail')}
            placeholder={t('auth.enterUsernameOrEmail')}
            value={loginData.username}
            onChange={handleChange}
            icon={<BiUser />}
            error={validationErrors.username}
            disabled={isLoading}
            autoComplete="username"
            required
          />
        </div>
        
        <div>
          <Input
            id="password"
            name="password"
            type="password"
            label={t('auth.password')}
            placeholder={t('auth.enterPassword')}
            value={loginData.password}
            onChange={handleChange}
            icon={<BiLock />}
            error={validationErrors.password}
            disabled={isLoading}
            autoComplete="current-password"
            required
          />
        </div>
        
        <div className="flex items-center justify-between">
          <Checkbox
            id="remember_me"
            name="remember_me"
            label={t('auth.rememberMe')}
            checked={loginData.remember_me}
            onChange={handleChange}
            disabled={isLoading}
          />
          
          <Link 
            to="/forgot-password" 
            className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          >
            {t('auth.forgotPassword')}
          </Link>
        </div>
        
        <Button
          type="submit"
          variant="primary"
          className="w-full"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <BiLoaderAlt className="animate-spin mr-2" />
              {t('common.loading')}
            </>
          ) : (
            t('auth.login')
          )}
        </Button>
        
        <div className="text-center mt-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('auth.noAccount')}{' '}
            <Link 
              to="/register" 
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            >
              {t('auth.signUp')}
            </Link>
          </p>
        </div>
      </form>
    </Card>
  );
};

export default LoginForm;