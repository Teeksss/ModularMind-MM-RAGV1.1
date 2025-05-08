import { Navigate } from 'react-router-dom';
import { useAppSelector } from '../../store/store';

interface AdminRouteProps {
  element: React.ReactNode;
  redirectTo?: string;
}

const AdminRoute: React.FC<AdminRouteProps> = ({
  element,
  redirectTo = '/dashboard'
}) => {
  const { user, isAuthenticated, loading } = useAppSelector(state => state.auth);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }
  
  return isAuthenticated && user?.role === 'admin' 
    ? <>{element}</> 
    : <Navigate to={redirectTo} replace />;
};

export default AdminRoute;