import React, { useState, useEffect } from 'react';
import { 
  Box, Container, Grid, Paper, Typography, Card, CardContent, CardHeader,
  Divider, Button, CircularProgress, Alert, List, ListItem, ListItemText, 
  Tabs, Tab, AppBar
} from '@mui/material';
import { useTheme } from '@mui/material/styles';

import ChatBox from '../components/ChatBox';
import DocumentExplorer from '../components/DocumentExplorer';
import { adminApi, embeddingApi, llmApi } from '../api/api';

// Şablondan panel bileşeni
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Dashboard = () => {
  const theme = useTheme();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [models, setModels] = useState({
    embedding: [],
    llm: []
  });
  
  // Sistem istatistiklerini ve modelleri yükle
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        // Paralel istekler
        const [statsResponse, embeddingModels, llmModels] = await Promise.all([
          adminApi.getSystemStats(),
          embeddingApi.getModels(),
          llmApi.getModels()
        ]);
        
        setStats(statsResponse);
        setModels({
          embedding: embeddingModels,
          llm: llmModels
        });
        
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };
    
    loadData();
  }, []);
  
  // Tab değişikliği
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  
  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      ) : (
        <Box>
          {/* İstatistik Kartları */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} md={4}>
              <Card elevation={3}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Vector Store
                  </Typography>
                  <Box display="flex" justifyContent="space-around" alignItems="center" sx={{ mt: 2 }}>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.vector_store?.total_documents || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Belge
                      </Typography>
                    </Box>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.vector_store?.total_chunks || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Metin Parçası
                      </Typography>
                    </Box>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.vector_store?.dimensions || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Vektör Boyutu
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card elevation={3}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Veri Ajanları
                  </Typography>
                  <Box display="flex" justifyContent="space-around" alignItems="center" sx={{ mt: 2 }}>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.agents?.total_agents || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Toplam Ajan
                      </Typography>
                    </Box>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.agents?.enabled_agents || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Aktif Ajan
                      </Typography>
                    </Box>
                    <Box textAlign="center">
                      <Typography variant="h4" color="success.main">
                        {stats?.agents?.successful_runs || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Başarılı Çalışma
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card elevation={3}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Konnektörler
                  </Typography>
                  <Box display="flex" justifyContent="space-around" alignItems="center" sx={{ mt: 2 }}>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.connectors?.total_connectors || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Toplam Konnektör
                      </Typography>
                    </Box>
                    <Box textAlign="center">
                      <Typography variant="h4" color="primary">
                        {stats?.connectors?.active_connectors || 0}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Aktif Bağlantı
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          {/* Ana İçerik Tabs */}
          <Box sx={{ mb: 3 }}>
            <AppBar position="static" color="default" elevation={0}>
              <Tabs
                value={activeTab}
                onChange={handleTabChange}
                indicatorColor="primary"
                textColor="primary"
                variant="fullWidth"
              >
                <Tab label="Doküman Yönetimi" />
                <Tab label="RAG Chat" />
                <Tab label="LLM Chat" />
              </Tabs>
            </AppBar>
            
            <Paper elevation={0} variant="outlined">
              <TabPanel value={activeTab} index={0}>
                <DocumentExplorer />
              </TabPanel>
              
              <TabPanel value={activeTab} index={1}>
                <ChatBox 
                  modelId="gpt-4o"
                  systemMessage="Verilen dokümanlardan bilgi çekerek detaylı cevaplar veren yardımcı bir asistansın."
                  ragEnabled={true}
                />
              </TabPanel>
              
              <TabPanel value={activeTab} index={2}>
                <Box sx={{ mb: 4 }}>
                  <Typography variant="h6" gutterBottom>
                    LLM Chat
                  </Typography>
                  <Typography variant="body2" color="textSecondary" paragraph>
                    LLM modellerinden birine doğrudan soru sorun. Bu modda RAG aktif değildir.
                  </Typography>
                  
                  <ChatBox 
                    modelId="gpt-4o"
                    systemMessage="Yardımcı bir AI asistanısın."
                    ragEnabled={false}
                  />
                </Box>
              </TabPanel>
            </Paper>
          </Box>
        </Box>
      )}
    </Container>
  );
};

export default Dashboard;