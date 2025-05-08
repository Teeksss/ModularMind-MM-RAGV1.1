import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImageSearchPanel from '../multimodal/ImageSearchPanel';
import { useMultimodalSearch } from '../../hooks/useMultimodalSearch';

// Mock the useMultimodalSearch hook
jest.mock('../../hooks/useMultimodalSearch');

describe('ImageSearchPanel', () => {
  const mockSearch = jest.fn();
  
  beforeEach(() => {
    // Reset the mock
    jest.clearAllMocks();
    
    // Setup the mock hook implementation
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: false,
      error: null
    });
  });
  
  it('renders the component with initial state', () => {
    render(<ImageSearchPanel />);
    
    // Check for main elements
    expect(screen.getByText('Multimodal Image Search')).toBeInTheDocument();
    expect(screen.getByText('Upload or Drag an Image')).toBeInTheDocument();
    expect(screen.getByText('Search Options')).toBeInTheDocument();
    
    // Check that the search button is disabled initially
    const searchButton = screen.getByRole('button', { name: /search/i });
    expect(searchButton).toBeDisabled();
  });
  
  it('enables the search button when text query is entered', () => {
    render(<ImageSearchPanel />);
    
    // Add text to the search input
    const searchInput = screen.getByPlaceholderText('Enter text to refine your search...');
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Check that the search button is now enabled
    const searchButton = screen.getByRole('button', { name: /search/i });
    expect(searchButton).not.toBeDisabled();
  });
  
  it('shows loading state during search', async () => {
    // Mock loading state
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: true,
      error: null
    });
    
    render(<ImageSearchPanel />);
    
    // Add text to the search input
    const searchInput = screen.getByPlaceholderText('Enter text to refine your search...');
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Verify loading spinner is shown
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
  
  it('shows advanced options when the show advanced button is clicked', () => {
    render(<ImageSearchPanel />);
    
    // Initially, advanced options should not be visible
    expect(screen.queryByText('Advanced search options coming soon...')).not.toBeInTheDocument();
    
    // Click the show advanced button
    const advancedButton = screen.getByRole('button', { name: /show advanced/i });
    fireEvent.click(advancedButton);
    
    // Now advanced options should be visible
    expect(screen.getByText('Advanced search options coming soon...')).toBeInTheDocument();
  });
  
  it('calls search function with correct params when search button is clicked', async () => {
    // Mock successful search with empty results
    mockSearch.mockResolvedValue({ results: [] });
    
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: false,
      error: null
    });
    
    render(<ImageSearchPanel />);
    
    // Add text to the search input
    const searchInput = screen.getByPlaceholderText('Enter text to refine your search...');
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Click search button
    const searchButton = screen.getByRole('button', { name: /search/i });
    fireEvent.click(searchButton);
    
    // Verify that search was called with correct parameters
    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith({
        image: null,
        text: 'test query',
        options: {
          limit: 10,
          filter: null
        }
      });
    });
  });
  
  it('displays error message when search fails', () => {
    // Mock error state
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: false,
      error: new Error('Test error message')
    });
    
    render(<ImageSearchPanel />);
    
    // Verify error message is displayed
    expect(screen.getByText('Error: Test error message')).toBeInTheDocument();
  });
});