import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../common/ErrorBoundary';

// Test component that throws an error
const ErrorThrowingComponent = () => {
  throw new Error('Test error');
};

// Mock console.error to avoid polluting test output
const originalConsoleError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalConsoleError;
});

describe('ErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Child component</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.getByText('Child component')).toBeInTheDocument();
  });
  
  it('renders fallback UI when an error occurs', () => {
    render(
      <ErrorBoundary>
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );
    
    // The error boundary should render the fallback UI
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/we're sorry/i)).toBeInTheDocument();
    
    // The error message should be displayed
    expect(screen.getByText('Error: Test error')).toBeInTheDocument();
    
    // The refresh button should be available
    expect(screen.getByRole('button', { name: /refresh page/i })).toBeInTheDocument();
  });
  
  it('renders custom fallback when provided', () => {
    const customFallback = <div data-testid="custom-fallback">Custom error UI</div>;
    
    render(
      <ErrorBoundary fallback={customFallback}>
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );
    
    // The custom fallback should be rendered
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.getByText('Custom error UI')).toBeInTheDocument();
    
    // The default fallback should not be rendered
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });
  
  it('calls onError when an error occurs', () => {
    const onError = jest.fn();
    
    render(
      <ErrorBoundary onError={onError}>
        <ErrorThrowingComponent />
      </ErrorBoundary>
    );
    
    // onError should have been called
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Test error' }),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });
});