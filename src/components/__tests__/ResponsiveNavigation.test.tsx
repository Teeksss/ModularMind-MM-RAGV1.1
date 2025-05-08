import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import ResponsiveNavigation from '../layout/ResponsiveNavigation';
import { useAuth } from '../../contexts/AuthContext';

// Mock the useAuth hook
jest.mock('../../contexts/AuthContext');

// Mock the location
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useLocation: () => ({
    pathname: '/dashboard'
  })
}));

describe('ResponsiveNavigation', () => {
  const mockLogout = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock regular user
    (useAuth as jest.Mock).mockReturnValue({
      user: {
        id: 'user123',
        name: 'Test User',
        email: 'test@example.com',
        role: 'user'
      },
      logout: mockLogout,
      isAuthenticated: true
    });
  });
  
  it('renders navigation with logo and links', () => {
    render(
      <BrowserRouter>
        <ResponsiveNavigation />
      </BrowserRouter>
    );
    
    // Logo should be visible
    expect(screen.getByAltText('ModularMind')).toBeInTheDocument();
    
    // Navigation links should be visible
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    
    // Admin links should NOT be visible for regular user
    expect(screen.queryByText('Users')).not.toBeInTheDocument();
  });
  
  it('shows admin links for admin users', () => {
    // Mock admin user
    (useAuth as jest.Mock).mockReturnValue({
      user: {
        id: 'admin123',
        name: 'Admin User',
        email: 'admin@example.com',
        role: 'admin'
      },
      logout: mockLogout,
      isAuthenticated: true
    });
    
    render(
      <BrowserRouter>
        <ResponsiveNavigation />
      </BrowserRouter>
    );
    
    // Admin links should be visible
    expect(screen.getByText('Users')).toBeInTheDocument();
  });
  
  it('toggles mobile menu when menu button is clicked', () => {
    const { container } = render(
      <BrowserRouter>
        <ResponsiveNavigation />
      </BrowserRouter>
    );
    
    // Mobile menu should be initially hidden
    expect(container.querySelector('#mobile-menu')).not.toBeInTheDocument();
    
    // Click the menu button
    const menuButton = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(menuButton);
    
    // Mobile menu should now be visible
    expect(container.querySelector('#mobile-menu')).toBeInTheDocument();
    
    // Close button should now be visible
    expect(screen.getByRole('button', { name: /close menu/i })).toBeInTheDocument();
  });
  
  it('toggles user dropdown when profile button is clicked', async () => {
    render(
      <BrowserRouter>
        <ResponsiveNavigation />
      </BrowserRouter>
    );
    
    // User dropdown should be initially hidden
    expect(screen.queryByText('Your Profile')).not.toBeInTheDocument();
    
    // Click the user profile button
    const userButton = screen.getByRole('button', { name: /open user menu/i });
    fireEvent.click(userButton);
    
    // User dropdown should now be visible
    expect(screen.getByText('Your Profile')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Sign out')).toBeInTheDocument();
  });
  
  it('calls logout function when sign out is clicked', () => {
    render(
      <BrowserRouter>
        <ResponsiveNavigation />
      </BrowserRouter>
    );
    
    // Open user dropdown
    const userButton = screen.getByRole('button', { name: /open user menu/i });
    fireEvent.click(userButton);
    
    // Click sign out button
    const signOutButton = screen.getByText('Sign out');
    fireEvent.click(signOutButton);
    
    // Logout function should have been called
    expect(mockLogout).toHaveBeenCalledTimes(1);
  });
  
  it('toggles search dropdown when search button is clicked', () => {
    render(
      <BrowserRouter>
        <ResponsiveNavigation />
      </BrowserRouter>
    );
    
    // Search dropdown should be initially hidden
    expect(screen.queryByText('Text Search')).not.toBeInTheDocument();
    
    // Click the search button
    const searchButton = screen.getByText('Search');
    fireEvent.click(searchButton);
    
    // Search dropdown should now be visible
    expect(screen.getByText('Text Search')).toBeInTheDocument();
    expect(screen.getByText('Image Search')).toBeInTheDocument();
    expect(screen.getByText('Audio Search')).toBeInTheDocument();
  });
});