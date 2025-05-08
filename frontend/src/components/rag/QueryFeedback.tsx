import React, { useState } from 'react';
import { FiThumbsUp, FiThumbsDown, FiSend, FiX } from 'react-icons/fi';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useToast } from '@/components/ui/use-toast';
import { api } from '@/lib/api';

interface QueryFeedbackProps {
  queryId: string;
}

const QueryFeedback: React.FC<QueryFeedbackProps> = ({ queryId }) => {
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [isHelpful, setIsHelpful] = useState<boolean | null>(null);
  const [comment, setComment] = useState('');
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [rating, setRating] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();
  
  const handleSubmitFeedback = async () => {
    if (isHelpful === null) return;
    
    const feedbackData = {
      query_id: queryId,
      rating: isHelpful ? 5 : 2, // Simple mapping: helpful = 5, not helpful = 2
      comment: comment,
      is_helpful: isHelpful
    };
    
    try {
      setIsSubmitting(true);
      
      await api.post('/api/v1/rag/feedback', feedbackData);
      
      setFeedbackSent(true);
      setShowCommentForm(false);
      
      toast({
        title: "Geri bildirim gönderildi",
        description: "Değerli görüşleriniz için teşekkür ederiz!",
        variant: "default"
      });
    } catch (error) {
      console.error('Feedback submission error:', error);
      toast({
        title: "Hata",
        description: "Geri bildiriminiz gönderilirken bir hata oluştu. Lütfen tekrar deneyin.",
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleFeedbackClick = (helpful: boolean) => {
    setIsHelpful(helpful);
    
    if (helpful) {
      // If helpful, just submit with default 5 rating
      handleSubmitFeedback();
    } else {
      // If not helpful, show comment form for additional feedback
      setShowCommentForm(true);
    }
  };
  
  return (
    <div className="w-full">
      {feedbackSent ? (
        <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center">
          <FiThumbsUp className="mr-1" size={14} />
          Geri bildiriminiz için teşekkürler!
        </div>
      ) : (
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">Bu yanıt yardımcı oldu mu?</span>
          
          <Button 
            variant="outline" 
            size="sm"
            className="h-8 px-2"
            onClick={() => handleFeedbackClick(true)}
            disabled={isSubmitting}
          >
            <FiThumbsUp className="mr-1" size={14} />
            Evet
          </Button>
          
          <Popover open={showCommentForm} onOpenChange={setShowCommentForm}>
            <PopoverTrigger asChild>
              <Button 
                variant="outline" 
                size="sm"
                className="h-8 px-2"
                onClick={() => handleFeedbackClick(false)}
                disabled={isSubmitting}
              >
                <FiThumbsDown className="mr-1" size={14} />
                Hayır
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80">
              <div className="space-y-3">
                <h4 className="font-medium">Geri Bildiriminizi Detaylandırın</h4>
                <p className="text-sm text-gray-500">
                  Yanıtın neden yardımcı olmadığını belirtmek ister misiniz?
                </p>
                
                <div className="space-y-2">
                  <Textarea 
                    placeholder="Yorumunuz (isteğe bağlı)"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    className="min-h-[80px]"
                  />
                </div>
                
                <div className="flex justify-end space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setShowCommentForm(false)}
                    disabled={isSubmitting}
                  >
                    <FiX className="mr-1" size={14} />
                    İptal
                  </Button>
                  
                  <Button 
                    size="sm"
                    onClick={handleSubmitFeedback}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-1" />
                    ) : (
                      <FiSend className="mr-1" size={14} />
                    )}
                    Gönder
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>
      )}
    </div>
  );
};

export default QueryFeedback;