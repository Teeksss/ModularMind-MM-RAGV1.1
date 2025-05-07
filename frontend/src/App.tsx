import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import Routes from './Routes';
import NotificationSystem from './components/common/NotificationSystem';
import GlobalErrorBoundary from './components/common/GlobalErrorBoundary';
import { useThemeContext } from './context/ThemeContext';
import './assets/css/main.css';

const App: React.FC = () => {
  const { theme } = useThemeContext();
  
  return (
    <div className={theme}>
      <Router>
        <GlobalErrorBoundary>
          <NotificationSystem />
          <Routes />
        </GlobalErrorBoundary>
      </Router>
    </div>
  );
};

export default App;