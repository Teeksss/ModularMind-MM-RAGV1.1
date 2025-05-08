import { renderHook, act } from '@testing-library/react-hooks';
import { useMultimodalSearch } from '../useMultimodalSearch';
import { apiClient } from '../../api/apiClient';

// Mock the apiClient
jest.mock('../../api/apiClient');

describe('useMultimodalSearch', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  it('should initialize with default state', () => {
    const { result } = renderHook(() => useMultimodalSearch());
    
    expect(result.current.results).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.additionalData).toBe(null);
  });
  
  it('should handle text search correctly', async () => {
    // Mock API response
    const mockResponse = {
      data: {
        results: [
          { id: '1', text: 'Result 1', score: 0.9 },
          { id: '2', text: 'Result 2', score: 0.8 }
        ]
      }
    };
    
    (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);
    
    const { result, waitForNextUpdate } = renderHook(() => useMultimodalSearch());
    
    // Execute search
    let searchPromise;
    act(() => {
      searchPromise = result.current.search({
        text: 'test query'
      });
    });
    
    // Should be in loading state
    expect(result.current.loading).toBe(true);
    
    await waitForNextUpdate();
    
    // Loading should be complete
    expect(result.current.loading).toBe(false);
    
    // Results should be updated
    expect(result.current.results).toEqual(mockResponse.data.results);
    
    // Error should remain null
    expect(result.current.error).toBe(null);
    
    // Search promise should resolve to response data
    await expect(searchPromise).resolves.toEqual(mockResponse.data);
    
    // API should have been called correctly
    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/multimodal/process',
      expect.any(FormData),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'multipart/form-data'
        })
      })
    );
  });
  
  it('should handle errors correctly', async () => {
    // Mock API error
    const mockError = new Error('API Error');
    (apiClient.post as jest.Mock).mockRejectedValue(mockError);
    
    const { result, waitForNextUpdate } = renderHook(() => useMultimodalSearch());
    
    // Execute search
    let searchPromise;
    act(() => {
      searchPromise = result.current.search({
        text: 'test query'
      });
    });
    
    await waitForNextUpdate();
    
    // Loading should be complete
    expect(result.current.loading).toBe(false);
    
    // Error should be set
    expect(result.current.error).toEqual(mockError);
    
    // Results should remain empty
    expect(result.current.results).toEqual([]);
    
    // Search promise should resolve to null
    await expect(searchPromise).resolves.toBe(null);
  });
  
  it('should extract additional data correctly', async () => {
    // Mock API response with additional data
    const mockResponse = {
      data: {
        results: [{ id: '1', text: 'Result 1', score: 0.9 }],
        audio_transcript: 'This is a transcript',
        image_caption: 'This is an image caption',
        embedding: [0.1, 0.2, 0.3]
      }
    };
    
    (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);
    
    const { result, waitForNextUpdate } = renderHook(() => useMultimodalSearch());
    
    // Execute search
    act(() => {
      result.current.search({
        text: 'test query',
        image: new File([''], 'test.jpg', { type: 'image/jpeg' })
      });
    });
    
    await waitForNextUpdate();
    
    // Additional data should be extracted
    expect(result.current.additionalData).toEqual({
      audio_transcript: 'This is a transcript',
      image_caption: 'This is an image caption',
      embedding: [0.1, 0.2, 0.3]
    });
  });
});