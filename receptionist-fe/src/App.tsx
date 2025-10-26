import { useEffect, useState } from 'react';
import { MessageSquare, Phone } from 'lucide-react';
import { ChatBox } from './components/ChatBox';
import { VoiceCallWidget } from './components/VoiceCallWidget';
import { BackgroundPattern } from './components/BackgroundPattern';
import { useConversationStore } from './store/conversationStore';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'voice'>('chat');
  const { conversationId } = useConversationStore();

  useEffect(() => {
    // Get initial tab from URL hash
    const hash = window.location.hash.slice(1) || 'chat';
    if (hash === 'chat' || hash === 'voice') {
      setActiveTab(hash);
    }
  }, []);

  useEffect(() => {
    console.log('App mounted with conversation ID:', conversationId);
  }, [conversationId]);

  const handleTabChange = (tab: 'chat' | 'voice') => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  return (
    <div className="app">
      <BackgroundPattern />
      <div className="container">
        <header className="app-header">
          <div className="header-content">
            <h1>Receptionist AI</h1>
            <p className="conversation-id">
              ID: <code>{conversationId}</code>
            </p>
          </div>
        </header>

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => handleTabChange('chat')}
          >
            <MessageSquare size={18} />
            <span>Chat</span>
          </button>
          <button
            className={`tab ${activeTab === 'voice' ? 'active' : ''}`}
            onClick={() => handleTabChange('voice')}
          >
            <Phone size={18} />
            <span>Voice Call</span>
          </button>
        </div>

        <div className="content">
          {activeTab === 'chat' && <ChatBox />}
          {activeTab === 'voice' && <VoiceCallWidget />}
        </div>
      </div>
    </div>
  );
}

export default App;
