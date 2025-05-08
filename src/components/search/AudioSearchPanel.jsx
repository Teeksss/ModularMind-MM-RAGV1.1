import React, { useState, useRef } from 'react';
import { 
  Box, Button, CircularProgress, Typography, 
  Card, CardContent, Grid, TextField,
  IconButton, Divider, Tooltip, Paper
} from '@mui/material';
import { Mic, Stop, Delete, Upload, Search } from '@mui/icons-material';
import { useMultimodalSearch } from '../../hooks/useMultimodalSearch';
import { AudioWaveform } from '../common/AudioWaveform';
import { useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';

const AudioSearchPanel = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showTranscript, setShowTranscript] = useState(false);
  const [transcript, setTranscript] = useState("");
  
  const { search, results, loading, error } = useMultimodalSearch();
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Start recording audio
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        setAudioURL(audioUrl);
        setAudioFile(audioBlob);
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Could not access microphone. Please check permissions.");
    }
  };

  // Stop recording audio
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Stop all tracks on the stream
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  // Handle audio file upload
  const handleAudioUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setAudioFile(file);
      setAudioURL(URL.createObjectURL(file));
    }
  };

  // Clear audio file
  const handleClearAudio = () => {
    setAudioFile(null);
    setAudioURL(null);
    setTranscript("");
    setShowTranscript(false);
  };

  // Perform search with audio
  const handleAudioSearch = async () => {
    if (!audioFile && !searchQuery) return;
    
    const result = await search({
      audio: audioFile,
      text: searchQuery,
      options: {
        limit: 10,
        transcribe: true
      }
    });
    
    // If we have a transcript from the API, show it
    if (result && result.audio_transcript) {
      setTranscript(result.audio_transcript);
      setShowTranscript(true);
    }
  };

  return (
    <Box sx={{ p: 2, width: '100%', maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Audio Search
      </Typography>
      <Divider sx={{ mb: 3 }} />
      
      <Grid container spacing={3}>
        {/* Audio Input Section */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined" sx={{ height: '100%', minHeight: 300 }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Record or Upload Audio
              </Typography>
              
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                {isRecording ? (
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<Stop />}
                    onClick={stopRecording}
                  >
                    Stop Recording
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<Mic />}
                    onClick={startRecording}
                    disabled={loading || audioFile !== null}
                  >
                    Start Recording
                  </Button>
                )}
                
                <Button
                  variant="outlined"
                  startIcon={<Upload />}
                  onClick={() => document.getElementById('audio-upload-input').click()}
                  disabled={loading || isRecording}
                  sx={{ ml: 2 }}
                >
                  Upload Audio
                </Button>
                <input
                  id="audio-upload-input"
                  type="file"
                  accept="audio/*"
                  style={{ display: 'none' }}
                  onChange={handleAudioUpload}
                />
              </Box>
              
              {audioURL && (
                <Box sx={{ mt: 2 }}>
                  <AudioWaveform 
                    audioUrl={audioURL} 
                    height={100}
                    width="100%"
                  />
                  
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
                    <audio controls src={audioURL} style={{ width: '100%' }} />
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
                    <IconButton color="error" onClick={handleClearAudio}>
                      <Delete />
                    </IconButton>
                  </Box>
                </Box>
              )}
              
              {showTranscript && transcript && (
                <Paper variant="outlined" sx={{ p: 2, mt: 2, bgcolor: 'background.paper' }}>
                  <Typography variant="subtitle2">Transcript:</Typography>
                  <Typography variant="body2">{transcript}</Typography>
                </Paper>
              )}
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
              
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<Search />}
                  onClick={handleAudioSearch}
                  disabled={loading || (!audioFile && !searchQuery)}
                >
                  {loading ? <CircularProgress size={24} /> : 'Search'}
                </Button>
              </Box>
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
          showAudioPreview={true}
          compact={isMobile}
        />
      </Box>
    </Box>
  );
};

export default AudioSearchPanel;