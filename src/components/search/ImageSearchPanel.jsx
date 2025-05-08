import React, { useState } from 'react';
import { 
  Box, Button, CircularProgress, Typography, 
  Card, CardMedia, CardContent, Grid,
  IconButton, Divider, Tooltip
} from '@mui/material';
import { UploadFile, Search, FilterAlt, ZoomIn } from '@mui/icons-material';
import { ImageDropzone } from '../common/ImageDropzone';
import { ImagePreview } from '../common/ImagePreview';
import { SearchResultsList } from '../results/SearchResultsList';
import { useMultimodalSearch } from '../../hooks/useMultimodalSearch';
import { useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';

const ImageSearchPanel = () => {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { search, results, loading, error } = useMultimodalSearch();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleImageUpload = (files) => {
    if (files && files[0]) {
      setImage(files[0]);
      // Create preview URL
      const previewUrl = URL.createObjectURL(files[0]);
      setImagePreview(previewUrl);
    }
  };

  const handleImageSearch = async () => {
    if (!image && !searchQuery) return;
    
    await search({
      image: image,
      text: searchQuery,
      options: {
        limit: 10,
        filter: showAdvanced ? {} : null
      }
    });
  };

  const handleClearImage = () => {
    setImage(null);
    setImagePreview(null);
  };

  return (
    <Box sx={{ p: 2, width: '100%', maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Multimodal Image Search
      </Typography>
      <Divider sx={{ mb: 3 }} />
      
      <Grid container spacing={3}>
        {/* Image Upload Section */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: '100%', minHeight: 300 }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Upload or Drag an Image
              </Typography>
              
              {imagePreview ? (
                <Box sx={{ position: 'relative', mt: 2 }}>
                  <ImagePreview 
                    src={imagePreview} 
                    alt="Uploaded image" 
                    onRemove={handleClearImage}
                  />
                </Box>
              ) : (
                <ImageDropzone onDrop={handleImageUpload} />
              )}
              
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<UploadFile />}
                  onClick={() => document.getElementById('image-upload-input').click()}
                  disabled={loading}
                >
                  Select Image
                </Button>
                <input
                  id="image-upload-input"
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(e) => handleImageUpload(e.target.files)}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Search Options Section */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Search Options
              </Typography>
              
              <TextField
                fullWidth
                label="Optional Text Query"
                variant="outlined"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                sx={{ mb: 2 }}
                disabled={loading}
              />
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<FilterAlt />}
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  disabled={loading}
                >
                  {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
                </Button>
                
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<Search />}
                  onClick={handleImageSearch}
                  disabled={loading || (!image && !searchQuery)}
                >
                  {loading ? <CircularProgress size={24} /> : 'Search'}
                </Button>
              </Box>
              
              {showAdvanced && (
                <Box sx={{ mt: 2 }}>
                  {/* Advanced search options would go here */}
                  <Typography variant="body2" color="textSecondary">
                    Advanced search options coming soon...
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      {/* Search Results */}
      <Box sx={{ mt: 4 }}>
        {error && (
          <Typography color="error" sx={{ mb: 2 }}>
            Error: {error.message}
          </Typography>
        )}
        
        <SearchResultsList 
          results={results} 
          loading={loading}
          showImagePreview={true}
          compact={isMobile}
        />
      </Box>
    </Box>
  );
};

export default ImageSearchPanel;