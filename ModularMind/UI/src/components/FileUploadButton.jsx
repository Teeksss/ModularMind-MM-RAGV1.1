import React, { useState } from 'react';
import { 
  Button, Dialog, DialogTitle, DialogContent, DialogActions, 
  Box, LinearProgress, Typography, FormControl, InputLabel, 
  MenuItem, Select, TextField, FormHelperText, Alert
} from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';

import { ragApi } from '../api/api';

const FileUploadButton = ({ 
  variant = "outlined", 
  size = "small", 
  onFileUploaded = () => {}, 
  onError = () => {} 
}) => {
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [options, setOptions] = useState({
    chunkSize: 500,
    chunkOverlap: 50,
    embeddingModel: ''
  });
  
  // Dialog aç
  const handleOpen = () => {
    setOpen(true);
    setSelectedFile(null);
    setUploading(false);
    setProgress(0);
    setError(null);
  };
  
  // Dialog kapat
  const handleClose = () => {
    setOpen(false);
  };
  
  // Dosya seçimi
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };
  
  // Dosya yükleme
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Lütfen bir dosya seçin');
      return;
    }
    
    try {
      setUploading(true);
      setProgress(0);
      setError(null);
      
      // Dosya tipini kontrol et
      const validExtensions = ['.txt', '.pdf', '.docx', '.md', '.csv', '.html'];
      const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
      
      if (!validExtensions.includes(extension)) {
        throw new Error(`Desteklenmeyen dosya türü: ${extension}. Desteklenen türler: ${validExtensions.join(', ')}`);
      }
      
      // İlerleme simulasyonu
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 500);
      
      // Dosyayı yükle
      const result = await ragApi.uploadFile(selectedFile, {
        chunk_size: options.chunkSize,
        chunk_overlap: options.chunkOverlap,
        embedding_model: options.embeddingModel || undefined
      });
      
      clearInterval(progressInterval);
      setProgress(100);
      
      // Sonucu bildir
      onFileUploaded(result);
      
      // Dialog kapat
      setTimeout(() => {
        setOpen(false);
        setUploading(false);
      }, 1000);
      
    } catch (err) {
      setError(err.message);
      setUploading(false);
      onError(err.message);
    }
  };
  
  return (
    <>
      <Button
        variant={variant}
        startIcon={<UploadIcon />}
        onClick={handleOpen}
        size={size}
      >
        Dosya Yükle
      </Button>
      
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>Dosya Yükle</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 1, mb: 2 }}>
            <Typography variant="body2" color="textSecondary" paragraph>
              Desteklenen dosya tipleri: TXT, PDF, DOCX, MD, CSV, HTML
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <input
                accept=".txt,.pdf,.docx,.md,.csv,.html"
                style={{ display: 'none' }}
                id="file-upload-button"
                type="file"
                onChange={handleFileChange}
                disabled={uploading}
              />
              <label htmlFor="file-upload-button">
                <Button
                  variant="contained"
                  component="span"
                  disabled={uploading}
                  fullWidth
                >
                  Dosya Seç
                </Button>
              </label>
              {selectedFile && (
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  Seçilen dosya: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
                </Typography>
              )}
            </Box>
            
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            
            <Typography variant="subtitle2" gutterBottom>
              Gelişmiş Ayarlar
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Chunk Boyutu"
                type="number"
                value={options.chunkSize}
                onChange={(e) => setOptions({ ...options, chunkSize: parseInt(e.target.value) || 0 })}
                disabled={uploading}
                size="small"
                fullWidth
                InputProps={{ inputProps: { min: 100, max: 2000 } }}
              />
              
              <TextField
                label="Chunk Örtüşme"
                type="number"
                value={options.chunkOverlap}
                onChange={(e) => setOptions({ ...options, chunkOverlap: parseInt(e.target.value) || 0 })}
                disabled={uploading}
                size="small"
                fullWidth
                InputProps={{ inputProps: { min: 0, max: 200 } }}
              />
            </Box>
            
            <FormControl fullWidth size="small">
              <InputLabel>Embedding Modeli</InputLabel>
              <Select
                value={options.embeddingModel}
                onChange={(e) => setOptions({ ...options, embeddingModel: e.target.value })}
                label="Embedding Modeli"
                disabled={uploading}
              >
                <MenuItem value="">
                  <em>Varsayılan</em>
                </MenuItem>
                <MenuItem value="openai">OpenAI Embeddings</MenuItem>
                <MenuItem value="local">Yerel Model</MenuItem>
              </Select>
              <FormHelperText>Boş bırakırsanız, varsayılan model kullanılır</FormHelperText>
            </FormControl>
          </Box>
          
          {uploading && (
            <Box sx={{ width: '100%', mt: 2 }}>
              <LinearProgress variant="determinate" value={progress} />
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
                <Typography variant="caption" color="textSecondary">
                  Yükleniyor... {progress}%
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={uploading}>
            İptal
          </Button>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            Yükle
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default FileUploadButton;