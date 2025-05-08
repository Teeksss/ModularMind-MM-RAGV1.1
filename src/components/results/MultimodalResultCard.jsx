import React, { useState } from 'react';
import {
  Card, CardContent, CardMedia, Typography, Box,
  Chip, IconButton, Collapse, Divider, Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Image as ImageIcon,
  AudioFile as AudioIcon,
  Article as ArticleIcon
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const ExpandMore = styled((props) => {
  const { expand, ...other } = props;
  return <IconButton {...other} />;
})(({ theme, expand }) => ({
  transform: !expand ? 'rotate(0deg)' : 'rotate(180deg)',
  marginLeft: 'auto',
  transition: theme.transitions.create('transform', {
    duration: theme.transitions.duration.shortest,
  }),
}));

const MultimodalResultCard = ({ result, compact = false }) => {
  const [expanded, setExpanded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = React.useRef(null);

  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  const handleCopyText = () => {
    navigator.clipboard.writeText(result.text);
  };

  const handleAudioToggle = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Determine the result type icon
  const getTypeIcon = () => {
    if (result.metadata?.type === 'image') return <ImageIcon />;
    if (result.metadata?.type === 'audio') return <AudioIcon />;
    return <ArticleIcon />;
  };

  return (
    <Card variant="outlined" sx={{ mb: 2, maxWidth: '100%' }}>
      {/* Card Header with Score and Type */}
      <Box sx={{ display: 'flex', alignItems: 'center', px: 2, pt: 1 }}>
        <Tooltip title={`Relevance: ${(result.score * 100).toFixed(1)}%`}>
          <Chip
            label={`${(result.score * 100).toFixed(1)}%`}
            color={result.score > 0.7 ? "success" : result.score > 0.4 ? "primary" : "default"}
            size="small"
            sx={{ mr: 1 }}
          />
        </Tooltip>
        
        <Tooltip title={result.metadata?.type || 'Document'}>
          <Chip
            icon={getTypeIcon()}
            label={result.metadata?.type || 'Document'}
            variant="outlined"
            size="small"
          />
        </Tooltip>
        
        <Box sx={{ ml: 'auto', display: 'flex' }}>
          <Tooltip title="Copy text">
            <IconButton onClick={handleCopyText} size="small">
              <CopyIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          
          <ExpandMore
            expand={expanded}
            onClick={handleExpandClick}
            aria-expanded={expanded}
            aria-label="show more"
            size="small"
          >
            <ExpandMoreIcon fontSize="small" />
          </ExpandMore>
        </Box>
      </Box>
      
      {/* Card Content */}
      <CardContent sx={{ pt: 1, pb: compact ? 1 : 2 }}>
        {/* If result has image and it's not compact view */}
        {result.metadata?.image_url && !compact && (
          <CardMedia
            component="img"
            image={result.metadata.image_url}
            alt={result.metadata?.title || "Image"}
            sx={{ 
              height: 140, 
              objectFit: 'contain',
              mb: 1,
              borderRadius: 1
            }}
          />
        )}
        
        {/* If result has audio */}
        {result.metadata?.audio_url && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <IconButton onClick={handleAudioToggle} color="primary">
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </IconButton>
            <audio 
              ref={audioRef}
              src={result.metadata.audio_url} 
              onEnded={() => setIsPlaying(false)}
              style={{ display: 'none' }}
            />
            <Typography variant="body2" color="text.secondary">
              {result.metadata?.audio_duration || 'Audio clip'}
            </Typography>
          </Box>
        )}
        
        {/* Document title/source if available */}
        {result.metadata?.title && (
          <Typography variant="subtitle1" gutterBottom>
            {result.metadata.title}
          </Typography>
        )}
        
        {/* Main text content */}
        <Typography 
          variant="body2" 
          color="text.primary"
          sx={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: expanded ? 'unset' : (compact ? 2 : 4),
            WebkitBoxOrient: 'vertical',
          }}
        >
          {result.text}
        </Typography>
      </CardContent>
      
      {/* Expanded content */}
      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Divider />
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Metadata
          </Typography>
          
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: 'max-content 1fr',
            gap: '4px 12px',
            fontSize: '0.85rem'
          }}>
            {Object.entries(result.metadata || {})
              .filter(([key]) => !['image_url', 'audio_url', 'type'].includes(key))
              .map(([key, value]) => (
                <React.Fragment key={key}>
                  <Box sx={{ color: 'text.secondary', fontWeight: 500 }}>
                    {key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}:
                  </Box>
                  <Box sx={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {typeof value === 'object' ? JSON.stringify(value) : value.toString()}
                  </Box>
                </React.Fragment>
              ))
            }
          </Box>
        </CardContent>
      </Collapse>
    </Card>
  );
};

export default MultimodalResultCard;