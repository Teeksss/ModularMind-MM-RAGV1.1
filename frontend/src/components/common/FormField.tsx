import React from 'react';
import { useFormContext } from 'react-hook-form';
import { FaExclamationCircle } from 'react-icons/fa';

interface FormFieldProps {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  labelClassName?: string;
  inputClassName?: string;
  errorClassName?: string;
  hint?: string;
  icon?: React.ReactNode;
  autoComplete?: string;
}

const FormField: React.FC<FormFieldProps> = ({
  name,
  label,
  type = 'text',
  placeholder,
  required = false,
  disabled = false,
  className = '',
  labelClassName = '',
  inputClassName = '',
  errorClassName = '',
  hint,
  icon,
  autoComplete,
}) => {
  const { register, formState: { errors } } = useFormContext();
  
  const error = errors[name];
  const errorMessage = error?.message as string | undefined;
  
  return (
    <div className={`mb-4 ${className}`}>
      <label 
        htmlFor={name} 
        className={`block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 ${labelClassName}`}
      >
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      
      <div className="relative">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {icon}
          </div>
        )}
        
        <input
          id={name}
          type={type}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={autoComplete}
          {...register(name)}
          className={`
            w-full px-4 py-2 border rounded-md shadow-sm 
            ${icon ? 'pl-10' : ''} 
            ${error ? 'border-red-300 dark:border-red-600 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500 focus:border-blue-500'} 
            dark:bg-gray-700 dark:text-white 
            disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed dark:disabled:bg-gray-800 dark:disabled:text-gray-400
            ${inputClassName}
          `}
        />
        
        {error && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <FaExclamationCircle className="text-red-500" />
          </div>
        )}
      </div>
      
      {errorMessage && (
        <p className={`mt-1 text-sm text-red-600 dark:text-red-400 ${errorClassName}`}>
          {errorMessage}
        </p>
      )}
      
      {hint && !error && (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {hint}
        </p>
      )}
    </div>
  );
};

export default FormField;