import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import ChatInterface from '../chat/ChatInterface';
import { useChatStore } from '../../store/chatStore';
import { useNotificationStore } from '../../store/notificationStore';

// Mock the stores
jest.mock('../../store/chatStore');
jest.mock('../../store/notificationStore');

// Mock the websocket hook
jest.mock('../../hooks/useWebSocket', () => ({
  __esModule: true,
  default: () => ({
    isConnected: true,
    subscribe: jest.fn(() => jest.fn()),
    sendMessage: jest.fn()
  })
}));

describe('ChatInterface Component', () => {
  // Setup common mocks
  beforeEach(() => {
    // Mock chat store
    (useChatStore as jest.Mock).mockReturnValue({
      messages: [],
      currentSession: null,
      isLoading: false,
      streaming: { isStreaming: false, sessionId: null, responseId: null, streamedContent: '' },
      sessions: [],
      fetchSessions: jest.fn(),
      sendMessage: jest.fn(),
      regenerateResponse: jest.fn(),
      clearMessages: jest.fn(),
      deleteSession: jest.fn(),
      createSession: jest.fn(),
      setCurrentSession: jest.fn(),
      renameSession: jest.fn()
    });

    // Mock notification store
    (useNotificationStore as jest.Mock).mockReturnValue({
      notifications: [],
      addNotification: jest.fn(),
      removeNotification: jest.fn()
    });
  });

  it('renders chat interface correctly', () => {
    render(<ChatInterface />);
    
    // Check if the chat form is rendered
    expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('handles message input correctly', () => {
    render(<ChatInterface />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    fireEvent.change(input, { target: { value: 'Hello, AI assistant!' } });
    expect(input).toHaveValue('Hello, AI assistant!');
  });

  it('sends a message when form is submitted', async () => {
    const sendMessageMock = jest.fn();
    (useChatStore as jest.Mock).mockReturnValue({
      messages: [],
      currentSession: null,
      isLoading: false,
      streaming: { isStreaming: false, sessionId: null, responseId: null, streamedContent: '' },
      sessions: [],
      fetchSessions: jest.fn(),
      sendMessage: sendMessageMock,
      regenerateResponse: jest.fn(),
      clearMessages: jest.fn(),
      deleteSession: jest.fn(),
      createSession: jest.fn(),
      setCurrentSession: jest.fn(),
      renameSession: jest.fn()
    });

    render(<ChatInterface />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    fireEvent.change(input, { target: { value: 'Hello, AI assistant!' } });
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    fireEvent.click(sendButton);
    
    expect(sendMessageMock).toHaveBeenCalledWith('Hello, AI assistant!');
  });

  it('displays messages correctly', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      messages: [
        { id: '1', session_id: 'session1', role: 'user', content: 'Hello', created_at: '2023-01-01T00:00:00Z' },
        { id: '2', session_id: 'session1', role: 'assistant', content: 'Hi there! How can I help you?', created_at: '2023-01-01T00:00:01Z' }
      ],
      currentSession: { id: 'session1', title: 'Chat Session', created_at: '2023-01-01T00:00:00Z' },
      isLoading: false,
      streaming: { isStreaming: false, sessionId: null, responseId: null, streamedContent: '' },
      sessions: [],
      fetchSessions: jest.fn(),
      sendMessage: jest.fn(),
      regenerateResponse: jest.fn(),
      clearMessages: jest.fn(),
      deleteSession: jest.fn(),
      createSession: jest.fn(),
      setCurrentSession: jest.fn(),
      renameSession: jest.fn()
    });

    render(<ChatInterface />);
    
    // Check if messages are displayed
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there! How can I help you?')).toBeInTheDocument();
  });

  it('shows loading state while waiting for response', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      messages: [
        { id: '1', session_id: 'session1', role: 'user', content: 'Hello', created_at: '2023-01-01T00:00:00Z' }
      ],
      currentSession: { id: 'session1', title: 'Chat Session', created_at: '2023-01-01T00:00:00Z' },
      isLoading: true,
      streaming: { isStreaming: false, sessionId: null, responseId: null, streamedContent: '' },
      sessions: [],
      fetchSessions: jest.fn(),
      sendMessage: jest.fn(),
      regenerateResponse: jest.fn(),
      clearMessages: jest.fn(),
      deleteSession: jest.fn(),
      createSession: jest.fn(),
      setCurrentSession: jest.fn(),
      renameSession: jest.fn()
    });

    render(<ChatInterface />);
    
    // Check loading indicator is shown
    expect(screen.getByText(/waiting for response/i)).toBeInTheDocument();
  });

  it('regenerates response when button is clicked', () => {
    const regenerateResponseMock = jest.fn();
    
    (useChatStore as jest.Mock).mockReturnValue({
      messages: [
        { id: '1', session_id: 'session1', role: 'user', content: 'Hello', created_at: '2023-01-01T00:00:00Z' },
        { id: '2', session_id: 'session1', role: 'assistant', content: 'Hi there!', created_at: '2023-01-01T00:00:01Z' }
      ],
      currentSession: { id: 'session1', title: 'Chat Session', created_at: '2023-01-01T00:00:00Z' },
      isLoading: false,
      streaming: { isStreaming: false, sessionId: null, responseId: null, streamedContent: '' },
      sessions: [],
      fetchSessions: jest.fn(),
      sendMessage: jest.fn(),
      regenerateResponse: regenerateResponseMock,
      clearMessages: jest.fn(),
      deleteSession: jest.fn(),
      createSession: jest.fn(),
      setCurrentSession: jest.fn(),
      renameSession: jest.fn()
    });

    render(<ChatInterface />);
    
    // Find regenerate button and click it
    const regenerateButton = screen.getByTestId('regenerate-button');
    fireEvent.click(regenerateButton);
    
    expect(regenerateResponseMock).toHaveBeenCalledWith('2');
  });
});