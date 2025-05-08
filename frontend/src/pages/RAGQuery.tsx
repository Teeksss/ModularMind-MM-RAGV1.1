import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FiSearch, FiLoader, FiFilter, FiClock, FiHelpCircle, FiSettings, FiInfo } from 'react-icons/fi';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/components/ui/use-toast';
import { Drawer, DrawerContent, DrawerTrigger, DrawerClose } from '@/components/ui/drawer';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import { useRagHistory } from '@/hooks/useRagHistory';
import Markdown from '@/components/common/Markdown';
import SourceViewer from '@/components/rag/SourceViewer';
import QueryFeedback from '@/components/rag/QueryFeedback';

interface Source {
  text: string;
  metadata: {
    source?: string;
    doc_id?: string;
    title?: string;
    url?: string;
    author?: string;
    date?: string;
    [key: string]: any;
  };
}

interface QueryResult {
  response: string;
  query_id: string;
  context_chunks: Source[];
  metrics: {
    latency_ms: number;
    token_count: number;
    context_size_tokens: number;
    chunk_count: number;
    precision?: number;
    recall?: number;
    faithfulness?: number;
  };
  processing_time_ms: number;
}

interface AdvancedOptions {
  useSemanticChunking: boolean;
  enableHierarchy: boolean;
  enableRecursive: boolean;
  contextSize: number;
  modelId: string;
  promptId: string;
}

const defaultAdvancedOptions: AdvancedOptions = {
  useSemanticChunking: true,
  enableHierarchy: true,
  enableRecursive: false,
  contextSize: 4000,
  modelId: 'default',
  promptId: 'default'
};

const RAGQuery: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  
  // State
  const [query, setQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [streamingResponse, setStreamingResponse] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('query');
  const [filters, setFilters] = useState<{[key: string]: any}>({});
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [advancedOptions, setAdvancedOptions] = useState<AdvancedOptions>(defaultAdvancedOptions);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  
  // Get history
  const { history, isLoading: isHistoryLoading, refresh: refreshHistory } = useRagHistory();
  
  // Refs
  const responseRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Get initial query from URL if present
  useEffect(() => {
    const urlQuery = searchParams.get('q');
    if (urlQuery) {
      setQuery(urlQuery);
    }
  }, [searchParams]);
  
  // Submit query
  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!query.trim()) {
      toast({
        title: "Sorgu gerekli",
        description: "Lütfen bir soru veya arama sorgusu girin.",
        variant: "destructive"
      });
      return;
    }
    
    // Set query parameter in URL
    setSearchParams({ q: query });
    
    // Clear previous results
    setResult(null);
    setStreamingResponse('');
    
    // Prepare request
    const requestData = {
      query: query,
      context_size: advancedOptions.contextSize,
      stream: false,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      model_id: advancedOptions.modelId !== 'default' ? advancedOptions.modelId : undefined,
      prompt_template_id: advancedOptions.promptId !== 'default' ? advancedOptions.promptId : undefined,
      retrieval_options: {
        semantic_chunking: advancedOptions.useSemanticChunking,
        hierarchical: advancedOptions.enableHierarchy,
        recursive: advancedOptions.enableRecursive
      }
    };
    
    try {
      setIsLoading(true);
      
      const response = await api.post('/api/v1/rag/query', requestData);
      
      setResult(response.data);
      setActiveTab('result');
      
      // Scroll to response
      setTimeout(() => {
        responseRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
      
      // Refresh history
      refreshHistory();
      
    } catch (error) {
      console.error('Query error:', error);
      toast({
        title: "Sorgu hatası",
        description: "Sorgunuz işlenirken bir hata oluştu. Lütfen tekrar deneyin.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  // Stream query
  const handleStreamQuery = async () => {
    if (!query.trim()) {
      toast({
        title: "Sorgu gerekli",
        description: "Lütfen bir soru veya arama sorgusu girin.",
        variant: "destructive"
      });
      return;
    }
    
    // Set query parameter in URL
    setSearchParams({ q: query });
    
    // Clear previous results
    setResult(null);
    setStreamingResponse('');
    
    // Prepare request
    const requestData = {
      query: query,
      context_size: advancedOptions.contextSize,
      stream: true,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      model_id: advancedOptions.modelId !== 'default' ? advancedOptions.modelId : undefined,
      prompt_template_id: advancedOptions.promptId !== 'default' ? advancedOptions.promptId : undefined,
      retrieval_options: {
        semantic_chunking: advancedOptions.useSemanticChunking,
        hierarchical: advancedOptions.enableHierarchy,
        recursive: advancedOptions.enableRecursive
      }
    };
    
    try {
      setIsLoading(true);
      setIsStreaming(true);
      setActiveTab('result');
      
      // Make streaming request
      const response = await fetch(`${api.defaults.baseURL}/api/v1/rag/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error('Response body is null');
      
      const decoder = new TextDecoder();
      let partialText = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        // Decode and append to response
        const text = decoder.decode(value, { stream: true });
        partialText += text;
        setStreamingResponse(partialText);
        
        // Auto scroll
        responseRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }
      
      // Refresh history
      refreshHistory();
      
    } catch (error) {
      console.error('Streaming error:', error);
      toast({
        title: "Streaming hatası",
        description: "Yanıt akışı sırasında bir hata oluştu. Lütfen tekrar deneyin.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };
  
  // Handle filter change
  const handleFilterChange = (key: string, value: any) => {
    if (value === '' || value === undefined || value === null) {
      const newFilters = { ...filters };
      delete newFilters[key];
      setFilters(newFilters);
    } else {
      setFilters(prev => ({ ...prev, [key]: value }));
    }
  };
  
  // Handle advanced options change
  const handleAdvancedChange = (key: keyof AdvancedOptions, value: any) => {
    setAdvancedOptions(prev => ({ ...prev, [key]: value }));
  };
  
  // Select history item
  const handleSelectHistoryItem = (query: string) => {
    setQuery(query);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };
  
  return (
    <div className="container mx-auto py-6 max-w-screen-xl">
      <div className="flex flex-col space-y-4">
        <h1 className="text-3xl font-bold">RAG Sorgu Arayüzü</h1>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="flex justify-between items-center mb-2">
            <TabsList>
              <TabsTrigger value="query">Sorgu</TabsTrigger>
              {(result || streamingResponse) && (
                <TabsTrigger value="result">Sonuç</TabsTrigger>
              )}
              <TabsTrigger value="history">Geçmiş</TabsTrigger>
            </TabsList>
            
            <div className="flex items-center space-x-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => setShowFilters(prev => !prev)}
                    >
                      <FiFilter className="mr-1" /> Filtreler
                      {Object.keys(filters).length > 0 && (
                        <Badge className="ml-1 text-xs">{Object.keys(filters).length}</Badge>
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    Arama sonuçlarını filtrelemek için kullanın
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => setShowAdvanced(prev => !prev)}
                    >
                      <FiSettings className="mr-1" /> Gelişmiş
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    RAG ayarlarını özelleştirin
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => navigate('/dashboard/rag-monitoring')}
                    >
                      <FiInfo className="mr-1" /> İzleme
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    RAG sistem izleme paneline git
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
          
          <TabsContent value="query" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Sorgu Gir</CardTitle>
                <CardDescription>
                  Bilgi almak istediğiniz soruyu veya arama sorgusunu girin.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid gap-4">
                    <div className="relative">
                      <Input
                        ref={inputRef}
                        placeholder="Sorgunuzu girin..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="pr-10"
                      />
                      {query && (
                        <button 
                          type="button" 
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          onClick={() => setQuery('')}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                    
                    {showFilters && (
                      <div className="p-4 border rounded-md bg-gray-50 dark:bg-gray-800 space-y-3">
                        <h3 className="font-medium">Filtreleme Seçenekleri</h3>
                        
                        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          <div className="space-y-1">
                            <label className="text-sm font-medium">Kaynak:</label>
                            <Input 
                              placeholder="Kaynak adı" 
                              value={filters.source || ''} 
                              onChange={(e) => handleFilterChange('source', e.target.value)}
                              size="sm"
                            />
                          </div>
                          
                          <div className="space-y-1">
                            <label className="text-sm font-medium">Yazar:</label>
                            <Input 
                              placeholder="Yazar adı" 
                              value={filters.author || ''} 
                              onChange={(e) => handleFilterChange('author', e.target.value)}
                              size="sm"
                            />
                          </div>
                          
                          <div className="space-y-1">
                            <label className="text-sm font-medium">Kategori:</label>
                            <Select 
                              value={filters.category || ''} 
                              onValueChange={(value) => handleFilterChange('category', value)}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Seçiniz" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="">Tümü</SelectItem>
                                <SelectItem value="documentation">Dokümantasyon</SelectItem>
                                <SelectItem value="article">Makale</SelectItem>
                                <SelectItem value="research">Araştırma</SelectItem>
                                <SelectItem value="tutorial">Öğretici</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div className="space-y-1">
                            <label className="text-sm font-medium">Tarih Sonrası:</label>
                            <Input 
                              type="date" 
                              value={filters.date_after || ''} 
                              onChange={(e) => handleFilterChange('date_after', e.target.value)}
                              size="sm"
                            />
                          </div>
                          
                          <div className="space-y-1">
                            <label className="text-sm font-medium">Tarih Öncesi:</label>
                            <Input 
                              type="date" 
                              value={filters.date_before || ''} 
                              onChange={(e) => handleFilterChange('date_before', e.target.value)}
                              size="sm"
                            />
                          </div>
                        </div>
                        
                        <div className="flex justify-end pt-2 space-x-2">
                          <Button 
                            type="button" 
                            variant="outline" 
                            size="sm"
                            onClick={() => setFilters({})}
                          >
                            Temizle
                          </Button>
                          <Button 
                            type="button" 
                            size="sm"
                            onClick={() => setShowFilters(false)}
                          >
                            Uygula
                          </Button>
                        </div>
                      </div>
                    )}
                    
                    {showAdvanced && (
                      <div className="p-4 border rounded-md bg-gray-50 dark:bg-gray-800 space-y-3">
                        <h3 className="font-medium">Gelişmiş Seçenekler</h3>
                        
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                              <Checkbox 
                                id="semantic-chunking"
                                checked={advancedOptions.useSemanticChunking}
                                onCheckedChange={(checked) => 
                                  handleAdvancedChange('useSemanticChunking', Boolean(checked))
                                }
                              />
                              <label 
                                htmlFor="semantic-chunking" 
                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                              >
                                Semantik Chunking
                              </label>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <FiHelpCircle className="text-gray-400" size={14} />
                                  </TooltipTrigger>
                                  <TooltipContent side="right" className="max-w-sm">
                                    Belgeleri anlamsal olarak bölümler, ilişkili içeriği bir arada tutar
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <Checkbox 
                                id="hierarchical"
                                checked={advancedOptions.enableHierarchy}
                                onCheckedChange={(checked) => 
                                  handleAdvancedChange('enableHierarchy', Boolean(checked))
                                }
                              />
                              <label 
                                htmlFor="hierarchical" 
                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                              >
                                Hiyerarşik Retrieval
                              </label>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <FiHelpCircle className="text-gray-400" size={14} />
                                  </TooltipTrigger>
                                  <TooltipContent side="right" className="max-w-sm">
                                    Belge yapısını korur, başlıklar ve alt başlıklar arasındaki ilişkileri saklar
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <Checkbox 
                                id="recursive"
                                checked={advancedOptions.enableRecursive}
                                onCheckedChange={(checked) => 
                                  handleAdvancedChange('enableRecursive', Boolean(checked))
                                }
                              />
                              <label 
                                htmlFor="recursive" 
                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                              >
                                Recursive Retrieval
                              </label>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <FiHelpCircle className="text-gray-400" size={14} />
                                  </TooltipTrigger>
                                  <TooltipContent side="right" className="max-w-sm">
                                    İlk sorgu sonuçlarından yeni sorgular üretir, daha derin ve kapsamlı bilgi alır
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          </div>
                          
                          <div className="space-y-3">
                            <div className="space-y-1">
                              <div className="flex justify-between">
                                <label htmlFor="context-size" className="text-sm font-medium">
                                  Context Boyutu: {advancedOptions.contextSize} token
                                </label>
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <FiHelpCircle className="text-gray-400" size={14} />
                                    </TooltipTrigger>
                                    <TooltipContent side="left" className="max-w-sm">
                                      LLM'e gönderilecek maksimum context penceresi boyutu
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              </div>
                              <Slider
                                id="context-size"
                                min={1000}
                                max={8000}
                                step={500}
                                value={[advancedOptions.contextSize]}
                                onValueChange={([value]) => handleAdvancedChange('contextSize', value)}
                              />
                            </div>
                            
                            <div className="space-y-1">
                              <label htmlFor="model-id" className="text-sm font-medium">
                                LLM Modeli
                              </label>
                              <Select
                                value={advancedOptions.modelId}
                                onValueChange={(value) => handleAdvancedChange('modelId', value)}
                              >
                                <SelectTrigger id="model-id">
                                  <SelectValue placeholder="Model seçin" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="default">Varsayılan</SelectItem>
                                  <SelectItem value="gpt-4">GPT-4</SelectItem>
                                  <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                                  <SelectItem value="llama3-70b">Llama 3 70B</SelectItem>
                                  <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            
                            <div className="space-y-1">
                              <label htmlFor="prompt-id" className="text-sm font-medium">
                                Prompt Şablonu
                              </label>
                              <Select
                                value={advancedOptions.promptId}
                                onValueChange={(value) => handleAdvancedChange('promptId', value)}
                              >
                                <SelectTrigger id="prompt-id">
                                  <SelectValue placeholder="Şablon seçin" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="default">Varsayılan</SelectItem>
                                  <SelectItem value="academic">Akademik Cevap</SelectItem>
                                  <SelectItem value="concise">Özet Cevap</SelectItem>
                                  <SelectItem value="detailed">Detaylı Açıklama</SelectItem>
                                  <SelectItem value="creative">Yaratıcı Yanıt</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex justify-end pt-2 space-x-2">
                          <Button 
                            type="button" 
                            variant="outline" 
                            size="sm"
                            onClick={() => setAdvancedOptions(defaultAdvancedOptions)}
                          >
                            Varsayılanlar
                          </Button>
                          <Button 
                            type="button" 
                            size="sm"
                            onClick={() => setShowAdvanced(false)}
                          >
                            Uygula
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button type="submit" disabled={isLoading || !query.trim()}>
                      {isLoading ? <Spinner size="sm" className="mr-2" /> : <FiSearch className="mr-2" />}
                      Sorgula
                    </Button>
                    
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={handleStreamQuery} 
                      disabled={isLoading || !query.trim()}
                    >
                      Streaming Yanıt
                    </Button>
                  </div>
                </form>
              </CardContent>
              <CardFooter className="text-sm text-muted-foreground">
                <p>Modern RAG teknolojisiyle bilgi kaynaklarınızda anında arama yapın.</p>
              </CardFooter>
            </Card>
            
            {/* Örnek sorgular */}
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">Örnek Sorgular</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2">
                  {[
                    "ModularMind RAG sisteminin mimari yapısı nasıldır?",
                    "2024 mali yılı için satış projeksiyonları nelerdir?",
                    "Yeni ürün özellikleri ve çıkış tarihleri hakkında bilgi ver",
                    "Müşteri memnuniyeti anketindeki en önemli bulgular nelerdir?",
                    "Şirket politikasına göre uzaktan çalışma kuralları nelerdir?"
                  ].map((example, i) => (
                    <Button 
                      key={i} 
                      variant="ghost" 
                      className="justify-start h-auto py-2 px-3 text-left"
                      onClick={() => handleSelectHistoryItem(example)}
                    >
                      {example}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="result" className="space-y-4">
            {(result || streamingResponse) ? (
              <div className="grid gap-4 grid-cols-1 lg:grid-cols-4">
                <div className="lg:col-span-3 space-y-4">
                  <Card>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle>Yanıt</CardTitle>
                          <CardDescription>
                            Sorgu: {query}
                          </CardDescription>
                        </div>
                        {result && (
                          <Badge variant="outline" className="flex items-center">
                            <FiClock className="mr-1" size={12} />
                            {result.processing_time_ms}ms
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div ref={responseRef} className="prose dark:prose-invert max-w-none">
                        {isStreaming ? (
                          <Spinner size="sm" className="mb-2" />
                        ) : null}
                        
                        <Markdown>
                          {streamingResponse || (result?.response || '')}
                        </Markdown>
                      </div>
                    </CardContent>
                    <CardFooter>
                      {result && (
                        <QueryFeedback queryId={result.query_id} />
                      )}
                    </CardFooter>
                  </Card>
                  
                  {result?.metrics && (
                    <Card>
                      <CardHeader className="py-3">
                        <CardTitle className="text-base">Metrikler</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                          <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                            <div className="text-sm text-gray-500 dark:text-gray-400">İşlem Süresi</div>
                            <div className="text-xl font-semibold">{result.metrics.latency_ms}ms</div>
                          </div>
                          
                          <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                            <div className="text-sm text-gray-500 dark:text-gray-400">Token Sayısı</div>
                            <div className="text-xl font-semibold">{result.metrics.token_count}</div>
                          </div>
                          
                          <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                            <div className="text-sm text-gray-500 dark:text-gray-400">Context Boyutu</div>
                            <div className="text-xl font-semibold">{result.metrics.context_size_tokens}</div>
                          </div>
                          
                          <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                            <div className="text