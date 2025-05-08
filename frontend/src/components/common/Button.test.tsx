import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button Component', () => {
  test('renders with default props', () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('btn');
    expect(button).toHaveClass('btn-primary');
    expect(button).toHaveClass('btn-md');
    expect(button).not.toHaveClass('w-full');
    expect(button).not.toHaveClass('rounded-full');
    expect(button).not.toBeDisabled();
  });

  test('renders with variant prop', () => {
    render(<Button variant="danger">Danger Button</Button>);
    const button = screen.getByRole('button', { name: /danger button/i });
    
    expect(button).toHaveClass('btn-danger');
    expect(button).not.toHaveClass('btn-primary');
  });

  test('renders with size prop', () => {
    render(<Button size="lg">Large Button</Button>);
    const button = screen.getByRole('button', { name: /large button/i });
    
    expect(button).toHaveClass('btn-lg');
    expect(button).not.toHaveClass('btn-md');
  });

  test('renders full width button', () => {
    render(<Button fullWidth>Full Width Button</Button>);
    const button = screen.getByRole('button', { name: /full width button/i });
    
    expect(button).toHaveClass('w-full');
  });

  test('renders rounded button', () => {
    render(<Button rounded>Rounded Button</Button>);
    const button = screen.getByRole('button', { name: /rounded button/i });
    
    expect(button).toHaveClass('rounded-full');
  });

  test('renders disabled button', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    
    expect(button).toBeDisabled();
    expect(button).toHaveClass('btn-disabled');
  });

  test('renders loading button', () => {
    render(<Button loading>Loading Button</Button>);
    
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toHaveClass('btn-loading');
    expect(screen.getByClass('loading')).toBeInTheDocument();
    expect(screen.queryByText(/loading button/i)).not.toBeInTheDocument();
  });

  test('renders with left icon', () => {
    const LeftIcon = () => <span data-testid="left-icon" />;
    render(<Button leftIcon={<LeftIcon />}>Icon Button</Button>);
    
    expect(screen.getByTestId('left-icon')).toBeInTheDocument();
    expect(screen.getByText(/icon button/i)).toBeInTheDocument();
  });

  test('renders with right icon', () => {
    const RightIcon = () => <span data-testid="right-icon" />;
    render(<Button rightIcon={<RightIcon />}>Icon Button</Button>);
    
    expect(screen.getByTestId('right-icon')).toBeInTheDocument();
    expect(screen.getByText(/icon button/i)).toBeInTheDocument();
  });

  test('calls onClick handler when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click Me</Button>);
    
    fireEvent.click(screen.getByRole('button', { name: /click me/i }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('does not call onClick when disabled', () => {
    const handleClick = jest.fn();
    render(<Button disabled onClick={handleClick}>Click Me</Button>);
    
    fireEvent.click(screen.getByRole('button', { name: /click me/i }));
    expect(handleClick).not.toHaveBeenCalled();
  });

  test('does not call onClick when loading', () => {
    const handleClick = jest.fn();
    render(<Button loading onClick={handleClick}>Click Me</Button>);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });
});