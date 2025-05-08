import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AudioSearchPanel from '../multimodal/AudioSearchPanel';
import { useMultimodalSearch } from '../../hooks/useMultimodalSearch';

// Mock the useMultimodalSearch hook
jest.mock('../../hooks/useMultimodalSearch');

// Mock the AudioWaveform component
jest.mock('../common/AudioWaveform', () => {
  return function MockAudioWaveform(props: any) {
    return <div data-testid="audio-waveform">Audio Waveform Mock</div>;
  };
});

// Mock the MediaDevices API
Object.defineProperty(window.navigator, 'mediaDevices', {
  value: {
    getUserMedia: jest.fn().mockImplementation(() => Promise.resolve({
      getTracks: () => [{ stop: jest.fn() }]
    }))
  },
  writable: true
});

describe('AudioSearchPanel', () => {
  const mockSearch = jest.fn();
  
  beforeEach(() => {
    // Reset the mock
    jest.clearAllMocks();
    
    // Setup the mock hook implementation
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: false,
      error: null,
      additionalData: null
    });
    
    // Setup URL.createObjectURL mock
    URL.createObjectURL = jest.fn(() => 'mock-audio-url');
    URL.revokeObjectURL = jest.fn();
  });
  
  it('renders the component with initial state', () => {
    render(<AudioSearchPanel />);
    
    // Check for main elements
    expect(screen.getByText('Audio Search')).toBeInTheDocument();
    expect(screen.getByText('Record or Upload Audio')).toBeInTheDocument();
    expect(screen.getByText('Search Options')).toBeInTheDocument();
    
    // Check that the search button is disabled initially
    const searchButton = screen.getByRole('button', { name: /search/i });
    expect(searchButton).toBeDisabled();
  });
  
  it('enables the search button when text query is entered', () => {
    render(<AudioSearchPanel />);
    
    // Add text to the search input
    const searchInput = screen.getByPlaceholderText('Enter text to refine your search...');
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Check that the search button is now enabled
    const searchButton = screen.getByRole('button', { name: /search/i });
    expect(searchButton).not.toBeDisabled();
  });
  
  it('shows recording UI when start recording is clicked', async () => {
    render(<AudioSearchPanel />);
    
    // Click the start recording button
    const recordButton = screen.getByRole('button', { name: /start recording/i });
    fireEvent.click(recordButton);
    
    // Wait for the UI to update
    await waitFor(() => {
      // Should now show stop recording button
      expect(screen.getByRole('button', { name: /stop recording/i })).toBeInTheDocument();
    });
  });
  
  it('displays transcript when available', async () => {
    // Mock search function that returns a transcript
    mockSearch.mockResolvedValue({
      results: [],
      audio_transcript: 'This is a test transcript'
    });
    
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: false,
      error: null,
      additionalData: null
    });
    
    render(<AudioSearchPanel />);
    
    // Add text to the search input
    const searchInput = screen.getByPlaceholderText('Enter text to refine your search...');
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Click search button
    const searchButton = screen.getByRole('button', { name: /search/i });
    fireEvent.click(searchButton);
    
    // Wait for transcript to appear
    await waitFor(() => {
      expect(screen.getByText('Transcript:')).toBeInTheDocument();
      expect(screen.getByText('This is a test transcript')).toBeInTheDocument();
    });
  });
  
  it('shows loading state during search', async () => {
    // Mock loading state
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: true,
      error: null,
      additionalData: null
    });
    
    render(<AudioSearchPanel />);
    
    // Add text to the search input
    const searchInput = screen.getByPlaceholderText('Enter text to refine your search...');
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Verify loading spinner is shown
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
  
  it('displays error message when search fails', () => {
    // Mock error state
    (useMultimodalSearch as jest.Mock).mockReturnValue({
      search: mockSearch,
      results: [],
      loading: false,
      error: new Error('Test error message'),
      additionalData: null
    });
    
    render(<AudioSearchPanel />);
    
    // Verify error message is displayed
    expect(screen.getByText('Error: Test error message')).toBeInTheDocument();
  });
});