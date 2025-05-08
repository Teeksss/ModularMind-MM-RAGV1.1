import React, { ButtonHTMLAttributes, ReactNode } from 'react';
import classNames from 'classnames';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'warning' | 'info' | 'ghost';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  rounded?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  loading = false,
  leftIcon,
  rightIcon,
  rounded = false,
  className,
  disabled,
  ...props
}) => {
  const buttonClasses = classNames(
    'btn',
    {
      // Variant styles
      'btn-primary': variant === 'primary',
      'btn-secondary': variant === 'secondary',
      'btn-danger': variant === 'danger',
      'btn-success': variant === 'success',
      'btn-warning': variant === 'warning',
      'btn-info': variant === 'info',
      'btn-ghost': variant === 'ghost',
      
      // Size styles
      'btn-xs': size === 'xs',
      'btn-sm': size === 'sm',
      'btn-md': size === 'md',
      'btn-lg': size === 'lg',
      'btn-xl': size === 'xl',
      
      // Full width
      'w-full': fullWidth,
      
      // Loading state
      'btn-loading': loading,
      
      // Disabled state
      'btn-disabled': disabled,
      
      // Rounded corners
      'rounded-full': rounded,
    },
    className
  );

  return (
    <button 
      className={buttonClasses} 
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="loading loading-spinner loading-sm"></span>
      ) : (
        <>
          {leftIcon && <span className="mr-2">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="ml-2">{rightIcon}</span>}
        </>
      )}
    </button>
  );
};

export default Button;