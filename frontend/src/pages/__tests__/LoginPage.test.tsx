import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from '../auth/LoginPage';
import { useAuthStore } from '../../store/authStore';
import { useNotificationStore } from '../../store/notificationStore';

// Mock the stores
jest.mock('../../store/authStore');
jest.mock('../../store/notificationStore');

// Mock the react-router hooks
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('LoginPage Component', () => {
  // Setup common mocks
  beforeEach(() => {
    // Mock auth store
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: jest.fn(),
      logout: jest.fn()
    });

    // Mock notification store
    (useNotificationStore as jest.Mock).mockReturnValue({
      notifications: [],
      addNotification: jest.fn(),
      removeNotification: jest.fn()
    });
  });

  it('renders login form correctly', () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    // Check if form elements are rendered
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('handles form input correctly', () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    
    expect(usernameInput).toHaveValue('testuser');
    expect(passwordInput).toHaveValue('password123');
  });

  it('calls login function when form is submitted with valid inputs', async () => {
    const loginMock = jest.fn().mockResolvedValue(undefined);
    
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: loginMock,
      logout: jest.fn()
    });
    
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('testuser', 'password123');
    });
  });

  it('shows error message when login fails', async () => {
    const loginMock = jest.fn().mockRejectedValue(new Error('Invalid credentials'));
    const addNotificationMock = jest.fn();
    
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: 'Invalid credentials',
      login: loginMock,
      logout: jest.fn()
    });
    
    (useNotificationStore as jest.Mock).mockReturnValue({
      notifications: [],
      addNotification: addNotificationMock,
      removeNotification: jest.fn()
    });
    
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('testuser', 'wrongpassword');
      expect(addNotificationMock).toHaveBeenCalledWith(expect.objectContaining({
        type: 'error'
      }));
    });
  });

  it('shows loading state during login process', async () => {
    // Mock a slow login function
    const loginMock = jest.fn().mockImplementation(() => {
      return new Promise(resolve => {
        setTimeout(() => resolve(undefined), 100);
      });
    });
    
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      error: null,
      login: loginMock,
      logout: jest.fn()
    });
    
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.click(submitButton);
    
    // Check if loading indicator is shown
    expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
  });
});