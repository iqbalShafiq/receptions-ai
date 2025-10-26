import { useEffect, useState } from 'react';
import { ChatBox } from './components/ChatBox';
import { VoiceCallWidget } from './components/VoiceCallWidget';
import { useConversationStore } from './store/conversationStore';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'voice'>('chat');
  const { conversationId } = useConversationStore();

  useEffect(() => {
    console.log('App mounted with conversation ID:', conversationId);
  }, [conversationId]);

  return (
    <div className="app">
      <div className="container">
        <header className="app-header">
          <div className="header-content">
            <h1>🤖 Receptionist AI</h1>
            <p className="conversation-id">
              Conversation ID: <code>{conversationId}</code>
            </p>
          </div>
          <div className="api-status">
            <span className="status-indicator">●</span> Ready
          </div>
        </header>

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chat
          </button>
          <button
            className={`tab ${activeTab === 'voice' ? 'active' : ''}`}
            onClick={() => setActiveTab('voice')}
          >
            🎤 Voice Call
          </button>
        </div>

        <div className="content">
          {activeTab === 'chat' && <ChatBox />}
          {activeTab === 'voice' && <VoiceCallWidget />}
        </div>

        <footer className="app-footer">
          <p>Backend API: {import.meta.env.VITE_API_URL || 'http://localhost:8000'}</p>
          <p>WebSocket: {import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
