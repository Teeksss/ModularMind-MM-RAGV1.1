import React, { useState, useEffect } from 'react';
import { 
  Box, Button, TextField, Typography, Paper, IconButton, 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  CircularProgress, Chip, Pagination, Grid, Card, CardContent, Divider,
  Accordion, AccordionSummary, AccordionDetails, Tooltip, Snackbar, Alert
} from '@mui/material';
import { 
  Delete as DeleteIcon, 
  Add as AddIcon,
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  FileCopy as FileCopyIcon
} from '@mui/icons-material';

import { ragApi } from '../api/api';
import FileUploadButton from './FileUploadButton';

const DocumentExplorer = () => {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [expandedDocId, setExpandedDocId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);
  const [stats, setStats] = useState(null);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  
  // Belgeleri yükle
  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Belgeleri al
      const result = await ragApi.listDocuments({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        filter_metadata: searchTerm ? { $text: searchTerm } : null
      });
      
      setDocuments(result.documents || []);
      setTotalCount(result.total || 0);
      
      // İstatistikleri al
      const statsData = await ragApi.getStats();
      setStats(statsData);
      
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };
  
  // İlk yükleme ve sayfa değişikliklerinde belgeleri yükle
  useEffect(() => {
    loadDocuments();
  }, [page, pageSize, searchTerm]);
  
  // Belge detaylarını yükle
  const loadDocumentDetails = async (documentId) => {
    try {
      setLoading(true);
      
      const document = await ragApi.getDocument(documentId);
      setSelectedDocument(document);
      
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };
  
  // Belge silme
  const handleDeleteDocument = async (documentId) => {
    try {
      setLoading(true);
      
      await ragApi.deleteDocument(documentId);
      
      // Belgeleri yeniden yükle
      await loadDocuments();
      
      setNotification({ 
        open: true, 
        message: 'Belge başarıyla silindi', 
        severity: 'success' 
      });
      
      setLoading(false);
      setConfirmDelete(null);
    } catch (err) {
      setError(err.message);
      setLoading(false);
      setConfirmDelete(null);
      
      setNotification({ 
        open: true, 
        message: `Hata: ${err.message}`, 
        severity: 'error' 
      });
    }
  };
  
  // Dosya yükleme tamamlandı
  const handleFileUploaded = async (result) => {
    setNotification({ 
      open: true, 
      message: `Dosya başarıyla yüklendi: ${result.document_id}`, 
      severity: 'success' 
    });
    
    // Belgeleri yeniden yükle
    await loadDocuments();
  };
  
  // Sayfa değiştirme
  const handlePageChange = (event, value) => {
    setPage(value);
  };
  
  // Belge görüntüleme
  const handleViewDocument = (documentId) => {
    if (expandedDocId === documentId) {
      setExpandedDocId(null);
    } else {
      setExpandedDocId(documentId);
      loadDocumentDetails(documentId);
    }
  };
  
  return (
    <Card elevation={3}>
      <CardContent>
        <Box mb={3}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h5">Belgeler</Typography>
            <Box>
              <FileUploadButton 
                onFileUploaded={handleFileUploaded}
                onError={(err) => setNotification({ open: true, message: err, severity: 'error' })}
              />
            </Box>
          </Box>
          
          {stats && (
            <Box mb={3}>
              <Paper elevation={0} sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="subtitle2" color="textSecondary">Toplam Belge</Typography>
                    <Typography variant="h6">{stats.total_documents}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="subtitle2" color="textSecondary">Toplam Chunk</Typography>
                    <Typography variant="h6">{stats.total_chunks}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Typography variant="subtitle2" color="textSecondary">Vector Boyutu</Typography>
                    <Typography variant="h6">{stats.dimensions}</Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Box>
          )}
          
          <Box mb={2} display="flex" gap={1}>
            <TextField
              fullWidth
              size="small"
              placeholder="Belge ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />
              }}
            />
          </Box>
          
          {loading && documents.length === 0 ? (
            <Box display="flex" justifyContent="center" p={4}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
          ) : documents.length === 0 ? (
            <Paper elevation={0} sx={{ p: 4, textAlign: 'center', bgcolor: '#f5f5f5' }}>
              <Typography variant="body1" color="textSecondary">
                Henüz hiç belge eklenmemiş.
              </Typography>
              <Box mt={2}>
                <FileUploadButton 
                  onFileUploaded={handleFileUploaded}
                  onError={(err) => setNotification({ open: true, message: err, severity: 'error' })}
                  variant="contained"
                />
              </Box>
            </Paper>
          ) : (
            <>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Belge ID</TableCell>
                      <TableCell>Başlık</TableCell>
                      <TableCell>Tür</TableCell>
                      <TableCell align="center">Parça Sayısı</TableCell>
                      <TableCell align="right">İşlemler</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {documents.map((doc) => (
                      <React.Fragment key={doc.id}>
                        <TableRow 
                          hover 
                          onClick={() => handleViewDocument(doc.id)}
                          sx={{ cursor: 'pointer' }}
                        >
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {doc.id}
                            </Typography>
                          </TableCell>
                          <TableCell>{doc.metadata?.title || 'İsimsiz'}</TableCell>
                          <TableCell>
                            <Chip 
                              size="small" 
                              label={doc.metadata?.source_type || doc.metadata?.file_type || 'Bilinmiyor'} 
                              color="primary" 
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell align="center">{doc.chunks?.length || 0}</TableCell>
                          <TableCell align="right">
                            <Tooltip title="Belgeyi Sil">
                              <IconButton 
                                size="small" 
                                color="error"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setConfirmDelete(doc.id);
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                        
                        {expandedDocId === doc.id && (
                          <TableRow>
                            <TableCell colSpan={5} sx={{ padding: 0, borderBottom: 0 }}>
                              <Box sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                                {loading ? (
                                  <Box display="flex" justifyContent="center" p={2}>
                                    <CircularProgress size={24} />
                                  </Box>
                                ) : selectedDocument ? (
                                  <Box>
                                    <Typography variant="subtitle1" gutterBottom>
                                      Belge Bilgileri
                                    </Typography>
                                    
                                    <Grid container spacing={2} sx={{ mb: 2 }}>
                                      {Object.entries(selectedDocument.metadata || {}).map(([key, value]) => (
                                        <Grid item xs={12} sm={6} md={4} key={key}>
                                          <Typography variant="caption" color="textSecondary">
                                            {key}
                                          </Typography>
                                          <Typography variant="body2">
                                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                          </Typography>
                                        </Grid>
                                      ))}
                                    </Grid>
                                    
                                    <Divider sx={{ my: 2 }} />
                                    
                                    <Typography variant="subtitle1" gutterBottom>
                                      Parçalar ({selectedDocument.chunks?.length || 0})
                                    </Typography>
                                    
                                    {selectedDocument.chunks?.map((chunk, index) => (
                                      <Accordion key={chunk.id} variant="outlined" sx={{ mb: 1 }}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                          <Typography variant="body2">
                                            Parça {index + 1} 
                                            <Typography component="span" variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                                              ({chunk.id})
                                            </Typography>
                                          </Typography>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                          <Box mb={2}>
                                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                                              {chunk.text}
                                            </Typography>
                                          </Box>
                                          
                                          <Tooltip title="Metni Kopyala">
                                            <IconButton 
                                              size="small" 
                                              onClick={() => {
                                                navigator.clipboard.writeText(chunk.text);
                                                setNotification({
                                                  open: true,
                                                  message: 'Metin panoya kopyalandı',
                                                  severity: 'success'
                                                });
                                              }}
                                            >
                                              <FileCopyIcon fontSize="small" />
                                            </IconButton>
                                          </Tooltip>
                                        </AccordionDetails>
                                      </Accordion>
                                    ))}
                                  </Box>
                                ) : (
                                  <Typography variant="body2" color="textSecondary">
                                    Belge yüklenemedi.
                                  </Typography>
                                )}
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              
              <Box display="flex" justifyContent="center" mt={2}>
                <Pagination 
                  count={Math.ceil(totalCount / pageSize)} 
                  page={page} 
                  onChange={handlePageChange} 
                  color="primary"
                />
              </Box>
            </>
          )}
        </Box>
      </CardContent>
      
      {/* Silme onay dialogu */}
      <Dialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
      >
        <DialogTitle>Belgeyi Sil</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Bu belgeyi silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(null)}>İptal</Button>
          <Button 
            onClick={() => handleDeleteDocument(confirmDelete)} 
            color="error" 
            variant="contained"
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Sil'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Bildirim snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={() => setNotification({ ...notification, open: false })}
      >
        <Alert 
          onClose={() => setNotification({ ...notification, open: false })} 
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Card>
  );
};

export default DocumentExplorer;