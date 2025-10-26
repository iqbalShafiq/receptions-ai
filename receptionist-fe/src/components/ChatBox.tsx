import { useEffect, useRef, useState } from 'react';
import { Send, MessageCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useConversationStore } from '../store/conversationStore';
import './ChatBox.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const ChatBox = () => {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { messages, addMessage, updateLastMessage, error, setError, conversationId } = useConversationStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea based on content
  const resizeTextarea = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    resizeTextarea();
  };

  const sendMessage = async (messageContent: string) => {
    const trimmedMessage = messageContent.trim();
    if (!trimmedMessage) return;

    // Add user message to store - preserve original formatting including newlines
    addMessage('user', messageContent);
    setInputValue('');
    setIsLoading(true);

    try {
      // Use streaming endpoint for real-time response
      const response = await fetch(`${API_URL}/chat-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: trimmedMessage,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let isStreaming = true;
      let messageAdded = false;

      while (isStreaming) {
        const { done, value } = await reader.read();
        if (done) {
          isStreaming = false;
          break;
        }

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix

              if (data.type === 'content') {
                // Accumulate content from stream
                fullResponse += data.data;

                // Add message on first chunk
                if (!messageAdded) {
                  addMessage('assistant', fullResponse);
                  messageAdded = true;
                } else {
                  // Update message with new accumulated content
                  updateLastMessage(fullResponse);
                }
              } else if (data.type === 'tool_call') {
                // Add tool call notification to response
                fullResponse += `\n*${data.data}*\n`;
                if (messageAdded) {
                  updateLastMessage(fullResponse);
                } else {
                  addMessage('assistant', fullResponse);
                  messageAdded = true;
                }
              } else if (data.type === 'done') {
                // Stream complete
                setError(null);
              } else if (data.type === 'error') {
                // Error occurred
                if (!messageAdded) {
                  addMessage('assistant', `Error: ${data.data}`);
                } else {
                  updateLastMessage(`Error: ${data.data}`);
                }
                setError(data.data);
              }
            } catch (e) {
              console.error('Failed to parse SSE message:', line, e);
            }
          }
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to send message';
      addMessage('assistant', `Error: ${errorMsg}`);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
      resizeTextarea();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter, unless Shift is held (Shift+Enter adds a newline)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  return (
    <div className="chat-box">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-content">
              <MessageCircle size={48} strokeWidth={1.5} />
              <p>No messages yet. Start a conversation!</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`message message-${msg.role}`}>
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>
              <div className="message-time">{msg.timestamp.toLocaleTimeString()}</div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message message-assistant">
            <div className="message-content">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <form onSubmit={handleSendMessage} className="chat-form">
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Shift+Enter for new line, Enter to send)"
          disabled={isLoading}
          className="chat-input"
          rows={1}
        />
        <button type="submit" disabled={isLoading} className="chat-submit" title="Send message">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
};
