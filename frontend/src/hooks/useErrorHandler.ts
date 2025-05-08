import { useCallback } from 'react';
import { useToast } from '@/components/ui/toast';
import { useTranslation } from 'react-i18next';
import * as Sentry from '@sentry/react';

interface ErrorOptions {
    shouldLog?: boolean;
    shouldNotify?: boolean;
    context?: Record<string, any>;
}

export const useErrorHandler = () => {
    const { t } = useTranslation();
    const { toast } = useToast();
    
    const handleError = useCallback((
        error: Error | string,
        options: ErrorOptions = {}
    ) => {
        const {
            shouldLog = true,
            shouldNotify = true,
            context = {}
        } = options;
        
        const errorMessage = error instanceof Error ? error.message : error;
        
        // Log error
        if (shouldLog) {
            console.error('Error occurred:', error);
            
            // Send to Sentry if in production
            if (process.env.NODE_ENV === 'production') {
                Sentry.captureException(error, {
                    extra: context
                });
            }
        }
        
        // Show notification
        if (shouldNotify) {
            toast({
                title: t('common.error'),
                description: t('errors.generic', { error: errorMessage }),
                variant: 'destructive',
                duration: 5000
            });
        }
        
        // Return error for chaining
        return error;
    }, [t, toast]);
    
    return { handleError };
};