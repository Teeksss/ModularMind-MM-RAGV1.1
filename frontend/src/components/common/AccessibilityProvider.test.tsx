import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { AccessibilityProvider, useAccessibility } from './AccessibilityProvider';

// Test bileşeni
const TestComponent = () => {
  const { settings, updateSettings, resetSettings } = useAccessibility();
  
  return (
    <div>
      <h1 data-testid="text-size-value">{settings.textSize}</h1>
      <div data-testid="high-contrast-value">{settings.highContrast ? 'true' : 'false'}</div>
      <div data-testid="reduce-motion-value">{settings.reduceMotion ? 'true' : 'false'}</div>
      
      <button 
        data-testid="increase-text-btn" 
        onClick={() => updateSettings({ textSize: settings.textSize + 0.1 })}
      >
        Increase Text
      </button>
      
      <button 
        data-testid="toggle-contrast-btn" 
        onClick={() => updateSettings({ highContrast: !settings.highContrast })}
      >
        Toggle Contrast
      </button>
      
      <button 
        data-testid="reset-btn" 
        onClick={resetSettings}
      >
        Reset
      </button>
    </div>
  );
};

describe('AccessibilityProvider', () => {
  
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    
    // Mock matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });
  
  test('provides default accessibility settings', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    expect(screen.getByTestId('text-size-value').textContent).toBe('1');
    expect(screen.getByTestId('high-contrast-value').textContent).toBe('false');
    expect(screen.getByTestId('reduce-motion-value').textContent).toBe('false');
  });
  
  test('updates settings when updateSettings is called', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    fireEvent.click(screen.getByTestId('increase-text-btn'));
    expect(screen.getByTestId('text-size-value').textContent).toBe('1.1');
    
    fireEvent.click(screen.getByTestId('toggle-contrast-btn'));
    expect(screen.getByTestId('high-contrast-value').textContent).toBe('true');
  });
  
  test('resets settings when resetSettings is called', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    // Change settings first
    fireEvent.click(screen.getByTestId('increase-text-btn'));
    fireEvent.click(screen.getByTestId('toggle-contrast-btn'));
    
    // Then reset
    fireEvent.click(screen.getByTestId('reset-btn'));
    
    // Check they're back to defaults
    expect(screen.getByTestId('text-size-value').textContent).toBe('1');
    expect(screen.getByTestId('high-contrast-value').textContent).toBe('false');
  });
  
  test('persists settings in localStorage', () => {
    const { unmount } = render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    // Change a setting
    fireEvent.click(screen.getByTestId('toggle-contrast-btn'));
    
    // Unmount and remount to simulate page refresh
    unmount();
    
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    // Setting should be persisted
    expect(screen.getByTestId('high-contrast-value').textContent).toBe('true');
  });
  
  test('applies CSS classes based on settings', () => {
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    // Initially no classes
    expect(document.documentElement.classList.contains('high-contrast')).toBe(false);
    
    // Toggle high contrast
    fireEvent.click(screen.getByTestId('toggle-contrast-btn'));
    
    // Class should be added
    expect(document.documentElement.classList.contains('high-contrast')).toBe(true);
    
    // Reset settings
    fireEvent.click(screen.getByTestId('reset-btn'));
    
    // Class should be removed
    expect(document.documentElement.classList.contains('high-contrast')).toBe(false);
  });
  
  test('detects system preferences', () => {
    // Mock system preference for reduced motion
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
    
    render(
      <AccessibilityProvider>
        <TestComponent />
      </AccessibilityProvider>
    );
    
    // Should detect system preference
    expect(screen.getByTestId('reduce-motion-value').textContent).toBe('true');
  });
  
  test('throws error when useAccessibility is used outside provider', () => {
    // Spy on console.error to prevent the error from being logged in tests
    jest.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAccessibility must be used within an AccessibilityProvider');
    
    // Restore console.error
    jest.restoreAllMocks();
  });
});