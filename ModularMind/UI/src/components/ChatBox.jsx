import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, TextField, Typography, Paper, IconButton, CircularProgress, Card, Divider, Tooltip } from '@mui/material';
import { Send as SendIcon, Delete as DeleteIcon, Save as SaveIcon, Settings as SettingsIcon } from '@mui/icons-material';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { llmApi } from '../api/api';

// Marked yapılandırması
marked.setOptions({
  breaks: true,
  gfm: true
});

const ChatBox = ({ 
  modelId = null, 
  systemMessage = "You are a helpful AI assistant.", 
  ragEnabled = false,
  onSettingsClick = null,
  height = '600px'
}) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const messageEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  
  // Konuşma geçmişini temizle
  const clearChat = () => {
    setMessages([]);
    setError(null);
  };
  
  // Konuşma geçmişini kaydet
  const saveChat = () => {
    const chatData = {
      messages,
      timestamp: new Date().toISOString(),
      model: modelId
    };
    
    // JSON olarak dışa aktar
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // İndirme bağlantısı oluştur
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    a.click();
    
    // URL'yi temizle
    URL.revokeObjectURL(url);
  };
  
  // Mesajları görünüme kaydır
  useEffect(() => {
    if (messageEndRef.current) {
      messageEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // RAG sorgusu gönder
  const sendRagQuery = async (text) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Kullanıcı mesajını ekle
      const userMessage = { role: 'user', content: text };
      setMessages(prev => [...prev, userMessage]);
      
      const response = await ragApi.query(text, {
        llm_model: modelId,
        system_message: systemMessage,
        include_sources: true
      });
      
      // Asistan mesajını ekle
      const botMessage = { role: 'assistant', content: response.answer, sources: response.sources };
      setMessages(prev => [...prev, botMessage]);
      
      setIsLoading(false);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };
  
  // LLM chat mesajı gönder
  const sendChatMessage = async (text) => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Kullanıcı mesajını ekle
      const userMessage = { role: 'user', content: text };
      const updatedMessages = [...messages, userMessage];
      setMessages(updatedMessages);
      
      // Sistem mesajını ekle
      const chatMessages = systemMessage 
        ? [{ role: 'system', content: systemMessage }, ...updatedMessages]
        : updatedMessages;
      
      // Sohbet yanıtı al
      const response = await llmApi.chatCompletion(chatMessages, modelId);
      
      // Asistan mesajını ekle
      setMessages(prev => [...prev, response.message]);
      
      setIsLoading(false);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };
  
  // Streaming chat yanıtı
  const streamChatResponse = (text) => {
    setIsLoading(true);
    setError(null);
    
    // Kullanıcı mesajını ekle
    const userMessage = { role: 'user', content: text };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    
    // Asistan mesajı için yer tutucu ekle
    const assistantMessage = { role: 'assistant', content: '' };
    setMessages([...updatedMessages, assistantMessage]);
    
    // Sistem mesajını ekle
    const chatMessages = systemMessage 
      ? [{ role: 'system', content: systemMessage }, ...updatedMessages]
      : updatedMessages;
    
    // Stream yanıtları almak için fonksiyon
    let responseText = '';
    
    const handleStream = (chunk, done, error) => {
      if (error) {
        setError(`Streaming hatası: ${error}`);
        setIsLoading(false);
        return;
      }
      
      if (done) {
        setIsLoading(false);
        return;
      }
      
      if (chunk) {
        responseText += chunk;
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'assistant', content: responseText };
          return updated;
        });
      }
    };
    
    // Streaming başlat
    const cancelStream = llmApi.streamingChat(chatMessages, handleStream, modelId);
    
    // Komponent temizlendiğinde stream'i kapat
    return cancelStream;
  };
  
  // Mesaj gönder
  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    const text = input.trim();
    setInput('');
    
    if (ragEnabled) {
      await sendRagQuery(text);
    } else {
      const cancelStream = streamChatResponse(text);
      
      // Komponenti temizlerken stream'i iptal et
      return () => {
        if (cancelStream) cancelStream();
      };
    }
  };
  
  // Enter tuşu ile mesaj gönder
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  // Markdown'ı HTML'e dönüştür
  const renderMarkdown = (content) => {
    const html = marked(content);
    const sanitized = DOMPurify.sanitize(html);
    return { __html: sanitized };
  };
  
  return (
    <Card elevation={3} sx={{ display: 'flex', flexDirection: 'column', height }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderBottom: '1px solid #e0e0e0' }}>
        <Typography variant="h6">
          {ragEnabled ? 'RAG Chat' : 'Chat'} {modelId && `(${modelId})`}
        </Typography>
        <Box>
          {onSettingsClick && (
            <Tooltip title="Ayarlar">
              <IconButton onClick={onSettingsClick} size="small">
                <SettingsIcon />
              </IconButton>
            </Tooltip>
          )}
          <Tooltip title="Konuşmayı Kaydet">
            <IconButton onClick={saveChat} size="small" disabled={messages.length === 0}>
              <SaveIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Konuşmayı Temizle">
            <IconButton onClick={clearChat} size="small" disabled={messages.length === 0}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      
      <Box 
        ref={chatContainerRef}
        sx={{ 
          flexGrow: 1, 
          overflowY: 'auto', 
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          bgcolor: '#f5f5f5'
        }}
      >
        {messages.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Typography variant="body2" color="text.secondary">
              Yeni bir konuşma başlatmak için mesaj gönderin.
            </Typography>
          </Box>
        ) : (
          messages.map((message, index) => (
            <Box 
              key={index} 
              sx={{ 
                alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%'
              }}
            >
              <Paper 
                elevation={1} 
                sx={{ 
                  p: 2, 
                  backgroundColor: message.role === 'user' ? '#e3f2fd' : '#ffffff',
                  borderRadius: 2
                }}
              >
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                  {message.role === 'user' ? 'Sen' : 'AI Asistan'}
                </Typography>
                
                <div 
                  className="markdown-content" 
                  dangerouslySetInnerHTML={renderMarkdown(message.content)} 
                />
                
                {message.sources && message.sources.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ my: 1 }} />
                    <Typography variant="caption" color="text.secondary">
                      Kaynaklar:
                    </Typography>
                    <Box component="ul" sx={{ mt: 1, pl: 2, fontSize: '0.875rem' }}>
                      {message.sources.map((source, idx) => (
                        <Box component="li" key={idx} sx={{ mb: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            {source.document_id} - {source.text_snippet}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
              </Paper>
            </Box>
          ))
        )}
        
        {error && (
          <Paper 
            elevation={1} 
            sx={{ 
              p: 2, 
              backgroundColor: '#ffebee', 
              borderRadius: 2,
              alignSelf: 'center',
              maxWidth: '80%'
            }}
          >
            <Typography variant="body2" color="error">
              Hata: {error}
            </Typography>
          </Paper>
        )}
        
        <div ref={messageEndRef} />
      </Box>
      
      <Box sx={{ p: 2, borderTop: '1px solid #e0e0e0' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Mesajınızı yazın..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            multiline
            maxRows={4}
            disabled={isLoading}
            size="small"
          />
          <Button
            variant="contained"
            color="primary"
            endIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
            onClick={handleSendMessage}
            disabled={isLoading || !input.trim()}
          >
            Gönder
          </Button>
        </Box>
      </Box>
    </Card>
  );
};

export default ChatBox;