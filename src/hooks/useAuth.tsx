import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../store/store';
import { login as loginAction, register as registerAction, logout as logoutAction, fetchCurrentUser } from '../store/slices/authSlice';
import { toast } from 'react-hot-toast';

export const useAuth = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { user, isAuthenticated, loading, error } = useAppSelector(state => state.auth);
  
  // Check auth status on mount
  useEffect(() => {
    // Only fetch user if we have a token but no user data
    const token = localStorage.getItem('authToken');
    if (token && !user && !loading) {
      dispatch(fetchCurrentUser());
    }
  }, [dispatch, user, loading]);
  
  // Show error notifications
  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error]);
  
  const login = async (email: string, password: string) => {
    try {
      const resultAction = await dispatch(loginAction({ email, password }));
      
      if (loginAction.fulfilled.match(resultAction)) {
        toast.success('Logged in successfully!');
        navigate('/dashboard');
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  };
  
  const register = async (userData: { name: string; email: string; password: string; organization?: string }) => {
    try {
      const resultAction = await dispatch(registerAction(userData));
      
      if (registerAction.fulfilled.match(resultAction)) {
        toast.success('Registration successful!');
        navigate('/dashboard');
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  };
  
  const logout = async () => {
    await dispatch(logoutAction());
    toast.success('Logged out successfully');
    navigate('/login');
  };
  
  return {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
    register
  };
};