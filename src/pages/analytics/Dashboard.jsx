import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Paper, Typography, CircularProgress,
  Card, CardContent, CardHeader, Divider, Button, 
  IconButton, Menu, MenuItem, List, ListItem, 
  ListItemText, Tooltip, Alert, Tab, Tabs
} from '@mui/material';
import {
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Search as SearchIcon,
  Storage as StorageIcon,
  Lightbulb as LightbulbIcon,
  MoreVert as MoreVertIcon,
  DateRange as DateRangeIcon,
  FileDownload as FileDownloadIcon
} from '@mui/icons-material';
import { ResponsiveLine } from '@nivo/line';
import { ResponsivePie } from '@nivo/pie';
import { ResponsiveBar } from '@nivo/bar';
import { apiClient } from '../../services/apiClient';
import { format, subDays } from 'date-fns';

// Date range options
const DATE_RANGES = [
  { label: 'Last 24 hours', value: 1 },
  { label: 'Last 7 days', value: 7 },
  { label: 'Last 30 days', value: 30 },
  { label: 'Last 90 days', value: 90 },
];

const AnalyticsDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metrics, setMetrics] = useState({
    queries: 0,
    documents: 0,
    searchTime: 0,
    topQueries: [],
  });
  const [queryMetrics, setQueryMetrics] = useState([]);
  const [modelUsage, setModelUsage] = useState([]);
  const [searchTypes, setSearchTypes] = useState([]);
  const [dateRange, setDateRange] = useState(7);
  const [anchorEl, setAnchorEl] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  
  // Menu state
  const open = Boolean(anchorEl);
  
  // Handle menu open
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  // Handle menu close
  const handleClose = () => {
    setAnchorEl(null);
  };
  
  // Handle date range change
  const handleDateRangeChange = (days) => {
    setDateRange(days);
    handleClose();
  };
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // Export data
  const handleExportData = () => {
    // Implementation for data export
    console.log('Export data');
    handleClose();
  };

  // Load analytics data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Format date range
        const startDate = format(subDays(new Date(), dateRange), 'yyyy-MM-dd');
        const endDate = format(new Date(), 'yyyy-MM-dd');
        
        // Fetch data
        const response = await apiClient.get('/api/analytics/dashboard', {
          params: { startDate, endDate }
        });
        
        // Set metrics
        setMetrics(response.data.summary);
        setQueryMetrics(response.data.queryData);
        setModelUsage(response.data.modelUsage);
        setSearchTypes(response.data.searchTypes);
        
      } catch (err) {
        console.error('Failed to load analytics data:', err);
        setError('Failed to load analytics data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [dateRange]);
  
  // Line chart colors
  const lineColors = { scheme: 'category10' };
  
  // Format percentage
  const formatPercent = (value) => `${value.toFixed(1)}%`;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3, alignItems: 'center' }}>
        <Typography variant="h5">Analytics Dashboard</Typography>
        
        <Box>
          <Button
            variant="outlined"
            startIcon={<DateRangeIcon />}
            onClick={handleClick}
            sx={{ mr: 1 }}
          >
            {DATE_RANGES.find(r => r.value === dateRange)?.label || 'Date Range'}
          </Button>
          
          <Menu
            anchorEl={anchorEl}
            open={open}
            onClose={handleClose}
          >
            {DATE_RANGES.map((range) => (
              <MenuItem 
                key={range.value}
                onClick={() => handleDateRangeChange(range.value)}
                selected={dateRange === range.value}
              >
                {range.label}
              </MenuItem>
            ))}
            <Divider />
            <MenuItem onClick={handleExportData}>
              <FileDownloadIcon fontSize="small" sx={{ mr: 1 }} />
              Export Data
            </MenuItem>
          </Menu>
        </Box>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Summary Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      bgcolor: 'primary.light', 
                      borderRadius: '50%', 
                      p: 1.2,
                      mr: 2,
                      display: 'flex',
                    }}>
                      <SearchIcon sx={{ color: 'primary.main' }} />
                    </Box>
                    <Box>
                      <Typography variant="h5" component="div" fontWeight="500">
                        {metrics.queries.toLocaleString()}
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        Total Searches
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      bgcolor: 'success.light', 
                      borderRadius: '50%', 
                      p: 1.2,
                      mr: 2,
                      display: 'flex',
                    }}>
                      <StorageIcon sx={{ color: 'success.main' }} />
                    </Box>
                    <Box>
                      <Typography variant="h5" component="div" fontWeight="500">
                        {metrics.documents.toLocaleString()}
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        Indexed Documents
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      bgcolor: 'warning.light', 
                      borderRadius: '50%', 
                      p: 1.2,
                      mr: 2,
                      display: 'flex',
                    }}>
                      <TimelineIcon sx={{ color: 'warning.main' }} />
                    </Box>
                    <Box>
                      <Typography variant="h5" component="div" fontWeight="500">
                        {metrics.searchTime.toFixed(2)}ms
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        Avg Response Time
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined">
                <CardContent sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      bgcolor: 'info.light', 
                      borderRadius: '50%', 
                      p: 1.2,
                      mr: 2,
                      display: 'flex',
                    }}>
                      <LightbulbIcon sx={{ color: 'info.main' }} />
                    </Box>
                    <Box>
                      <Typography variant="h5" component="div" fontWeight="500">
                        {metrics.relevanceScore ? `${(metrics.relevanceScore * 100).toFixed(1)}%` : 'N/A'}
                      </Typography>
                      <Typography color="text.secondary" variant="body2">
                        Avg Relevance Score
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          {/* Charts */}
          <Grid container spacing={3}>
            {/* Search Trends Chart */}
            <Grid item xs={12} md={8}>
              <Card variant="outlined" sx={{ height: 400 }}>
                <CardHeader 
                  title="Search Trends"
                  action={
                    <IconButton>
                      <MoreVertIcon />
                    </IconButton>
                  }
                  sx={{ pb: 0 }}
                />
                <CardContent sx={{ height: 350 }}>
                  <Tabs
                    value={tabValue}
                    onChange={handleTabChange}
                    sx={{ mb: 2 }}
                  >
                    <Tab label="Searches" />
                    <Tab label="Response Time" />
                    <Tab label="Relevance" />
                  </Tabs>
                  
                  {queryMetrics.length > 0 ? (
                    <Box sx={{ height: 280 }}>
                      <ResponsiveLine
                        data={[
                          {
                            id: tabValue === 0 ? 'Searches' : tabValue === 1 ? 'Response Time (ms)' : 'Relevance Score',
                            data: queryMetrics.map(item => ({
                              x: item.date,
                              y: tabValue === 0 ? item.count : 
                                 tabValue === 1 ? item.avgTime : 
                                 item.relevanceScore
                            }))
                          }
                        ]}
                        margin={{ top: 20, right: 30, bottom: 50, left: 60 }}
                        xScale={{ type: '