import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  FaThumbsUp, FaThumbsDown, FaRegThumbsUp, FaRegThumbsDown, 
  FaStar, FaRegStar, FaPaperPlane, FaTimes
} from 'react-icons/fa';
import { apiService } from '../../services/api';
import { useNotificationStore } from '../../store/notificationStore';

interface ResponseFeedbackProps {
  responseId: string;
  queryId: string;
  sources?: Array<{
    id: string;
    title: string;
  }>;
  onFeedbackSubmitted?: (rating: number, isHelpful: boolean) => void;
}

const ResponseFeedback: React.FC<ResponseFeedbackProps> = ({
  responseId,
  queryId,
  sources = [],
  onFeedbackSubmitted
}) => {
  const { t } = useTranslation();
  const { addNotification } = useNotificationStore();
  
  // State
  const [isHelpful, setIsHelpful] = useState<boolean | null>(null);
  const [rating, setRating] = useState<number>(0);
  const [showDetailedFeedback, setShowDetailedFeedback] = useState<boolean>(false);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [isMissingInfo, setIsMissingInfo] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  
  // Handle helpful/not helpful click
  const handleHelpfulClick = (helpful: boolean) => {
    if (isSubmitted) return;
    setIsHelpful(helpful);
    
    // If thumbs down, show detailed feedback form
    if (!helpful) {
      setShowDetailedFeedback(true);
    }
  };
  
  // Handle star rating click
  const handleRatingClick = (newRating: number) => {
    if (isSubmitted) return;
    setRating(newRating);
    
    // If low rating (1-2), show detailed feedback form
    if (newRating <= 2) {
      setShowDetailedFeedback(true);
    }
  };
  
  // Handle source selection
  const handleSourceSelect = (sourceId: string) => {
    if (isSubmitted) return;
    
    setSelectedSources(prev => {
      // If already selected, remove it
      if (prev.includes(sourceId)) {
        return prev.filter(id => id !== sourceId);
      }
      // Otherwise add it
      return [...prev, sourceId];
    });
  };
  
  // Submit feedback
  const handleSubmitFeedback = async () => {
    if (isSubmitted || isSubmitting) return;
    
    // Don't submit if no rating or helpful status
    if (rating === 0 && isHelpful === null) {
      addNotification({
        type: 'warning',
        title: t('feedback.missingRating'),
        message: t('feedback.pleaseRateResponse')
      });
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Prepare feedback data
      const feedbackData = {
        response_id: responseId,
        query_id: queryId,
        rating,
        helpful: isHelpful,
        feedback_text: feedbackText.trim() || undefined,
        selected_sources: selectedSources.length > 0 ? selectedSources : undefined,
        missing_information: isMissingInfo || undefined
      };
      
      // Submit feedback
      await apiService.post('/feedback/submit', feedbackData);
      
      // Mark as submitted
      setIsSubmitted(true);
      setShowDetailedFeedback(false);
      
      // Show success notification
      addNotification({
        type: 'success',
        title: t('feedback.thankYou'),
        message: t('feedback.feedbackReceived')
      });
      
      // Call callback if provided
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted(rating, isHelpful || false);
      }
      
    } catch (error) {
      console.error('Error submitting feedback:', error);
      
      // Show error notification
      addNotification({
        type: 'error',
        title: t('feedback.error'),
        message: t('feedback.errorSubmittingFeedback')
      });
      
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Cancel detailed feedback
  const handleCancelDetailedFeedback = () => {
    setShowDetailedFeedback(false);
  };
  
  // If already submitted, show thank you message
  if (isSubmitted) {
    return (
      <div className="feedback-thankyou text-center my-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-md">
        <p className="text-green-700 dark:text-green-300 font-medium">
          {t('feedback.thankYouForFeedback')}
        </p>
      </div>
    );
  }
  
  return (
    <div className="response-feedback mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
      {/* Initial feedback options */}
      {!showDetailedFeedback && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {t('feedback.wasThisHelpful')}
            </span>
            
            <button
              onClick={() => handleHelpfulClick(true)}
              className={`p-2 rounded-full ${
                isHelpful === true
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
              aria-label={t('feedback.helpful')}
            >
              {isHelpful === true ? <FaThumbsUp /> : <FaRegThumbsUp />}
            </button>
            
            <button
              onClick={() => handleHelpfulClick(false)}
              className={`p-2 rounded-full ${
                isHelpful === false
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
              aria-label={t('feedback.notHelpful')}
            >
              {isHelpful === false ? <FaThumbsDown /> : <FaRegThumbsDown />}
            </button>
          </div>
          
          {/* Star Rating */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {t('feedback.rateResponse')}
            </span>
            
            <div className="flex items-center">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleRatingClick(star)}
                  className={`p-1 ${
                    rating >= star
                      ? 'text-yellow-500 dark:text-yellow-400'
                      : 'text-gray-300 dark:text-gray-600 hover:text-gray-400 dark:hover:text-gray-500'
                  }`}
                  aria-label={t('feedback.rateStars', { count: star })}
                >
                  {rating >= star ? <FaStar /> : <FaRegStar />}
                </button>
              ))}
            </div>
          </div>
          
          {/* Show detailed feedback button */}
          <button
            onClick={() => setShowDetailedFeedback(true)}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            {t('feedback.provideFeedback')}
          </button>
        </div>
      )}
      
      {/* Detailed feedback form */}
      {showDetailedFeedback && (
        <div className="detailed-feedback mt-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {t('feedback.detailedFeedback')}
            </h3>
            
            <button
              onClick={handleCancelDetailedFeedback}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              aria-label={t('common.close')}
            >
              <FaTimes />
            </button>
          </div>
          
          {/* Feedback text area */}
          <div className="mb-4">
            <label 
              htmlFor="feedback-text" 
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              {t('feedback.feedbackDetails')}
            </label>
            <textarea
              id="feedback-text"
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              rows={3}
              placeholder={t('feedback.enterFeedback')}
            />
          </div>
          
          {/* Sources selection */}
          {sources.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('feedback.helpfulSources')}
              </label>
              
              <div className="space-y-2">
                {sources.map((source) => (
                  <div key={source.id} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`source-${source.id}`}
                      checked={selectedSources.includes(source.id)}
                      onChange={() => handleSourceSelect(source.id)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                    />
                    <label
                      htmlFor={`source-${source.id}`}
                      className="ml-2 text-sm text-gray-700 dark:text-gray-300"
                    >
                      {source.title}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Missing information checkbox */}
          <div className="mb-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="missing-info"
                checked={isMissingInfo}
                onChange={() => setIsMissingInfo(!isMissingInfo)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
              />
              <label
                htmlFor="missing-info"
                className="ml-2 text-sm text-gray-700 dark:text-gray-300"
              >
                {t('feedback.missingInformation')}
              </label>
            </div>
          </div>
          
          {/* Submit button */}
          <div className="flex justify-end">
            <button
              onClick={handleCancelDetailedFeedback}
              className="mr-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </button>
            
            <button
              onClick={handleSubmitFeedback}
              className="px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full" />
                  {t('common.submitting')}
                </>
              ) : (
                <>
                  <FaPaperPlane className="mr-2" />
                  {t('common.submit')}
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseFeedback;