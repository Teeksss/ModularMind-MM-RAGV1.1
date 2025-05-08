import React, { useState, useEffect } from 'react';
import { apiClient } from '../../api/apiClient';
import { 
  FiBarChart2, FiClock, FiSearch, FiDatabase, FiCalendar, 
  FiDownload, FiFilter, FiRefreshCw 
} from 'react-icons/fi';
import { 
  ResponsiveLine, 
  ResponsivePie, 
  ResponsiveBar 
} from '@nivo/charts';
import { format, subDays } from 'date-fns';

// Date range options
const DATE_RANGES = [
  { label: 'Last 24 hours', value: 1 },
  { label: 'Last 7 days', value: 7 },
  { label: 'Last 30 days', value: 30 },
  { label: 'Last 90 days', value: 90 },
];

type SummaryMetrics = {
  queries: number;
  documents: number;
  searchTime: number;
  relevanceScore: number;
  totalUsers: number;
};

type QueryMetric = {
  date: string;
  count: number;
  avgTime: number;
  relevanceScore: number;
};

type ModelUsage = {
  id: string;
  value: number;
  label: string;
};

type SearchType = {
  type: string;
  count: number;
};

type TopQuery = {
  query: string;
  count: number;
};

const AnalyticsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState(7);
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  
  const [metrics, setMetrics] = useState<SummaryMetrics>({
    queries: 0,
    documents: 0,
    searchTime: 0,
    relevanceScore: 0,
    totalUsers: 0
  });
  
  const [queryMetrics, setQueryMetrics] = useState<QueryMetric[]>([]);
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([]);
  const [searchTypes, setSearchTypes] = useState<SearchType[]>([]);
  const [topQueries, setTopQueries] = useState<TopQuery[]>([]);
  
  // Fetch analytics data
  useEffect(() => {
    fetchData();
  }, [dateRange]);
  
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Format date range
      const startDate = format(subDays(new Date(), dateRange), 'yyyy-MM-dd');
      const endDate = format(new Date(), 'yyyy-MM-dd');
      
      // Fetch analytics data
      const response = await apiClient.get('/api/analytics/dashboard', {
        params: { startDate, endDate }
      });
      
      // Set data
      if (response.data) {
        setMetrics(response.data.summary);
        setQueryMetrics(response.data.queryData);
        setModelUsage(response.data.modelUsage);
        setSearchTypes(response.data.searchTypes);
        setTopQueries(response.data.topQueries);
      }
    } catch (err) {
      console.error('Failed to load analytics data:', err);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle date range change
  const handleDateRangeChange = (days: number) => {
    setDateRange(days);
    setShowFilterMenu(false);
  };
  
  // Export data as CSV
  const exportData = () => {
    // Build CSV content
    let csv = 'date,queries,avgTime,relevanceScore\n';
    
    queryMetrics.forEach(metric => {
      csv += `${metric.date},${metric.count},${metric.avgTime},${metric.relevanceScore}\n`;
    });
    
    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', `modularmind-analytics-${format(new Date(), 'yyyy-MM-dd')}.csv`);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };
  
  // Line chart for search trends
  const lineChartData = [
    {
      id: activeTab === 0 ? 'Searches' : activeTab === 1 ? 'Response Time (ms)' : 'Relevance Score',
      data: queryMetrics.map(item => ({
        x: item.date,
        y: activeTab === 0 ? item.count : 
           activeTab === 1 ? item.avgTime : 
           item.relevanceScore * 100 // Convert to percentage
      }))
    }
  ];
  
  // Line chart theme
  const lineChartTheme = {
    axis: {
      ticks: {
        text: {
          fontSize: 12,
          fill: '#4b5563'
        }
      },
      legend: {
        text: {
          fontSize: 12,
          fill: '#4b5563'
        }
      }
    },
    grid: {
      line: {
        stroke: '#e5e7eb',
        strokeWidth: 1
      }
    },
    crosshair: {
      line: {
        stroke: '#3b82f6',
        strokeWidth: 1,
        strokeOpacity: 0.75
      }
    },
    tooltip: {
      container: {
        background: 'white',
        color: '#1f2937',
        fontSize: 12,
        borderRadius: 4,
        boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
      }
    }
  };
  
  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Analytics Dashboard</h1>
        
        <div className="flex space-x-2">
          <button
            onClick={fetchData}
            className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-full transition-colors"
            title="Refresh data"
          >
            <FiRefreshCw className="w-5 h-5" />
          </button>
          
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
            >
              <FiCalendar className="mr-2" />
              {DATE_RANGES.find(r => r.value === dateRange)?.label || 'Date Range'}
            </button>
            
            {showFilterMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border border-gray-200">
                <div className="py-1">
                  {DATE_RANGES.map((range) => (
                    <button
                      key={range.value}
                      onClick={() => handleDateRangeChange(range.value)}
                      className={`block w-full text-left px-4 py-2 text-sm ${
                        dateRange === range.value 
                          ? 'bg-blue-50 text-blue-700' 
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      {range.label}
                    </button>
                  ))}
                  
                  <div className="border-t border-gray-100 my-1"></div>
                  
                  <button
                    onClick={exportData}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <FiDownload className="inline mr-2" />
                    Export Data
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
          {error}
        </div>
      )}
      
      {loading && metrics.queries === 0 ? (
        <div className="flex justify-center items-center h-64">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 mb-6">
            {/* Total Searches */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-blue-100 text-blue-600 mr-4">
                  <FiSearch className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Total Searches</p>
                  <p className="text-2xl font-semibold text-gray-900">{metrics.queries.toLocaleString()}</p>
                </div>
              </div>
            </div>
            
            {/* Indexed Documents */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-green-100 text-green-600 mr-4">
                  <FiDatabase className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Indexed Documents</p>
                  <p className="text-2xl font-semibold text-gray-900">{metrics.documents.toLocaleString()}</p>
                </div>
              </div>
            </div>
            
            {/* Avg Response Time */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-yellow-100 text-yellow-600 mr-4">
                  <FiClock className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Avg Response Time</p>
                  <p className="text-2xl font-semibold text-gray-900">{metrics.searchTime.toFixed(2)}ms</p>
                </div>
              </div>
            </div>
            
            {/* Relevance Score */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-purple-100 text-purple-600 mr-4">
                  <FiBarChart2 className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Avg Relevance</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {metrics.relevanceScore ? `${(metrics.relevanceScore * 100).toFixed(1)}%` : 'N/A'}
                  </p>
                </div>
              </div>
            </div>
            
            {/* Total Users */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-indigo-100 text-indigo-600 mr-4">
                  <FiBarChart2 className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Total Users</p>
                  <p className="text-2xl font-semibold text-gray-900">{metrics.totalUsers}</p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            {/* Search Trends Chart */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm lg:col-span-2">
              <div className="mb-4">
                <h2 className="text-lg font-medium text-gray-900">Search Trends</h2>
              </div>
              
              <div className="mb-4 border-b border-gray-200">
                <nav className="-mb-px flex space-x-6">
                  <button
                    onClick={() => setActiveTab(0)}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 0
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Search Volume
                  </button>
                  <button
                    onClick={() => setActiveTab(1)}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 1
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Response Time
                  </button>
                  <button
                    onClick={() => setActiveTab(2)}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 2
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Relevance
                  </button>
                </nav>
              </div>
              
              <div className="h-72">
                {queryMetrics.length > 0 ? (
                  <ResponsiveLine
                    data={lineChartData}
                    margin={{ top: 20, right: 20, bottom: 50, left: 50 }}
                    xScale={{ type: 'point' }}
                    yScale={{ 
                      type: 'linear', 
                      min: 'auto', 
                      max: 'auto', 
                      stacked: false, 
                      reverse: false 
                    }}
                    axisBottom={{
                      tickSize: 5,
                      tickPadding: 5,
                      tickRotation: -45,
                      legend: 'Date',
                      legendOffset: 36,
                      legendPosition: 'middle'
                    }}
                    axisLeft={{
                      tickSize: 5,
                      tickPadding: 5,
                      tickRotation: 0,
                      legend: activeTab === 0 ? 'Count' : activeTab === 1 ? 'Time (ms)' : 'Score (%)',
                      legendOffset: -40,
                      legendPosition: 'middle'
                    }}
                    colors={{ scheme: 'category10' }}
                    pointSize={8}
                    pointColor={{ theme: 'background' }}
                    pointBorderWidth={2}
                    pointBorderColor={{ from: 'serieColor' }}
                    pointLabelYOffset={-12}
                    useMesh={true}
                    theme={lineChartTheme}
                    curve="monotoneX"
                    animate={true}
                    motionConfig="gentle"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    No data available for the selected period
                  </div>
                )}
              </div>
            </div>
            
            {/* Model Distribution Pie Chart */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="mb-4">
                <h2 className="text-lg font-medium text-gray-900">Model Usage</h2>
              </div>
              
              <div className="h-72">
                {modelUsage.length > 0 ? (
                  <ResponsivePie
                    data={modelUsage}
                    margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                    innerRadius={0.5}
                    padAngle={0.7}
                    cornerRadius={3}
                    activeOuterRadiusOffset={8}
                    colors={{ scheme: 'paired' }}
                    borderWidth={1}
                    borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
                    arcLinkLabelsSkipAngle={10}
                    arcLinkLabelsTextColor="#333333"
                    arcLinkLabelsThickness={2}
                    arcLinkLabelsColor={{ from: 'color' }}
                    arcLabelsSkipAngle={10}
                    arcLabelsTextColor={{ from: 'color', modifiers: [['darker', 2]] }}
                    animate={true}
                    motionConfig="gentle"
                    legends={[
                      {
                        anchor: 'bottom',
                        direction: 'row',
                        justify: false,
                        translateX: 0,
                        translateY: 56,
                        itemsSpacing: 0,
                        itemWidth: 100,
                        itemHeight: 18,
                        itemTextColor: '#999',
                        itemDirection: 'left-to-right',
                        itemOpacity: 1,
                        symbolSize: 18,
                        symbolShape: 'circle'
                      }
                    ]}
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    No model usage data available
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Bottom row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Search Types Bar Chart */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="mb-4">
                <h2 className="text-lg font-medium text-gray-900">Search Types</h2>
              </div>
              
              <div className="h-72">
                {searchTypes.length > 0 ? (
                  <ResponsiveBar
                    data={searchTypes.map(item => ({
                      type: item.type,
                      count: item.count
                    }))}
                    keys={['count']}
                    indexBy="type"
                    margin={{ top: 20, right: 20, bottom: 50, left: 60 }}
                    padding={0.3}
                    valueScale={{ type: 'linear' }}
                    indexScale={{ type: 'band', round: true }}
                    colors={{ scheme: 'nivo' }}
                    borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
                    axisTop={null}
                    axisRight={null}
                    axisBottom={{
                      tickSize: 5,
                      tickPadding: 5,
                      tickRotation: 0,
                      legend: 'Search Type',
                      legendPosition: 'middle',
                      legendOffset: 40
                    }}
                    axisLeft={{
                      tickSize: 5,
                      tickPadding: 5,
                      tickRotation: 0,
                      legend: 'Count',
                      legendPosition: 'middle',
                      legendOffset: -50
                    }}
                    labelSkipWidth={12}
                    labelSkipHeight={12}
                    labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
                    animate={true}
                    motionConfig="gentle"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    No search type data available
                  </div>
                )}
              </div>
            </div>
            
            {/* Top Queries */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
              <div className="mb-4">
                <h2 className="text-lg font-medium text-gray-900">Top Queries</h2>
              </div>
              
              {topQueries.length > 0 ? (
                <div className="overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Query
                        </th>
                        <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Count
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {topQueries.map((query, index) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 truncate max-w-xs">
                            {query.query}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                            {query.count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="flex h-72 items-center justify-center text-gray-500">
                  No query data available
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AnalyticsDashboard;