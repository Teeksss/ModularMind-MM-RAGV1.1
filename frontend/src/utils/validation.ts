import * as yup from 'yup';
import i18n from '../i18n';

/**
 * Validation schemas for forms
 */
export const validationSchemas = {
  // Login form validation schema
  login: yup.object({
    username: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.username') }))
      .min(3, i18n.t('validation.minLength', { field: i18n.t('auth.username'), length: 3 })),
    password: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.password') }))
      .min(6, i18n.t('validation.minLength', { field: i18n.t('auth.password'), length: 6 }))
  }),
  
  // Registration form validation schema
  register: yup.object({
    username: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.username') }))
      .min(3, i18n.t('validation.minLength', { field: i18n.t('auth.username'), length: 3 }))
      .matches(/^[a-zA-Z0-9_]+$/, i18n.t('validation.alphanumeric', { field: i18n.t('auth.username') })),
    email: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.email') }))
      .email(i18n.t('validation.email')),
    password: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.password') }))
      .min(8, i18n.t('validation.minLength', { field: i18n.t('auth.password'), length: 8 }))
      .matches(
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/,
        i18n.t('validation.password')
      ),
    confirmPassword: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.confirmPassword') }))
      .oneOf([yup.ref('password')], i18n.t('validation.passwordMatch'))
  }),
  
  // Feedback form validation schema
  feedback: yup.object({
    rating: yup
      .number()
      .min(1, i18n.t('validation.required', { field: i18n.t('feedback.rating') }))
      .max(5, i18n.t('validation.invalid', { field: i18n.t('feedback.rating') }))
      .required(i18n.t('validation.required', { field: i18n.t('feedback.rating') })),
    feedbackText: yup
      .string()
      .when('rating', {
        is: (rating: number) => rating <= 3,
        then: yup.string().required(i18n.t('validation.requiredForLowRating')),
        otherwise: yup.string()
      })
  }),
  
  // Document upload validation schema
  documentUpload: yup.object({
    title: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('documents.title') }))
      .max(100, i18n.t('validation.maxLength', { field: i18n.t('documents.title'), length: 100 })),
    description: yup
      .string()
      .max(500, i18n.t('validation.maxLength', { field: i18n.t('documents.description'), length: 500 })),
    file: yup
      .mixed()
      .required(i18n.t('validation.fileRequired'))
      .test('fileSize', i18n.t('validation.fileSize', { size: '10MB' }), (value) => {
        if (!value) return false;
        return value.size <= 10 * 1024 * 1024; // 10MB
      })
      .test('fileType', i18n.t('validation.fileType'), (value) => {
        if (!value) return false;
        
        const acceptedTypes = [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // docx
          'application/msword', // doc
          'text/plain',
          'text/markdown',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation', // pptx
          'application/vnd.ms-powerpoint' // ppt
        ];
        
        return acceptedTypes.includes(value.type);
      })
  }),
  
  // Search validation schema
  search: yup.object({
    query: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('search.query') }))
      .min(2, i18n.t('validation.minLength', { field: i18n.t('search.query'), length: 2 }))
  }),
  
  // Profile update validation schema
  profile: yup.object({
    name: yup
      .string()
      .max(100, i18n.t('validation.maxLength', { field: i18n.t('profile.name'), length: 100 })),
    email: yup
      .string()
      .required(i18n.t('validation.required', { field: i18n.t('auth.email') }))
      .email(i18n.t('validation.email')),
    currentPassword: yup
      .string()
      .when('newPassword', {
        is: (val: string) => val && val.length > 0,
        then: yup.string().required(i18n.t('validation.required', { field: i18n.t('profile.currentPassword') }))
      }),
    newPassword: yup
      .string()
      .min(8, i18n.t('validation.minLength', { field: i18n.t('profile.newPassword'), length: 8 }))
      .matches(
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/,
        i18n.t('validation.password')
      )
      .nullable(), // Allow empty for no password change
    confirmNewPassword: yup
      .string()
      .when('newPassword', {
        is: (val: string) => val && val.length > 0,
        then: yup.string()
          .required(i18n.t('validation.required', { field: i18n.t('profile.confirmPassword') }))
          .oneOf([yup.ref('newPassword')], i18n.t('validation.passwordMatch'))
      })
  })
};

/**
 * Format validation errors from Yup
 */
export const formatYupErrors = (err: any): Record<string, string> => {
  const errors: Record<string, string> = {};
  if (err.inner) {
    err.inner.forEach((e: any) => {
      errors[e.path] = e.message;
    });
  }
  return errors;
};

/**
 * Validate form data against a schema
 */
export const validateForm = async <T extends Record<string, any>>(
  schema: yup.ObjectSchema<any>,
  data: T
): Promise<{ isValid: boolean; errors: Record<string, string> }> => {
  try {
    await schema.validate(data, { abortEarly: false });
    return { isValid: true, errors: {} };
  } catch (err) {
    const errors = formatYupErrors(err);
    return { isValid: false, errors };
  }
};