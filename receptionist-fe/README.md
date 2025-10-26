# Receptionist AI - Frontend

Frontend React application untuk Receptionist AI system dengan dukungan **Chat** dan **Voice Call** menggunakan WebSocket real-time.

## 🚀 Setup

### Prerequisites
- Node.js 18+
- npm 9+
- Backend API running di `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local jika backend running di host berbeda
```

### Development

```bash
# Start dev server (http://localhost:5173)
npm run dev

# Build untuk production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
receptionist-fe/
├── src/
│   ├── components/
│   │   ├── ChatBox.tsx          # Chat interface component
│   │   ├── ChatBox.css
│   │   ├── VoiceCallWidget.tsx  # Voice call interface
│   │   └── VoiceCallWidget.css
│   ├── hooks/
│   │   ├── useWebSocket.ts      # WebSocket connection hook
│   │   └── useAudioRecorder.ts  # Audio recording hook
│   ├── store/
│   │   └── conversationStore.ts # Zustand state management
│   ├── types/
│   │   └── api.ts              # TypeScript types for API
│   ├── App.tsx                  # Main app component
│   ├── App.css
│   ├── main.tsx
│   └── index.css
├── .env.example
├── .env.local
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 🎯 Features

### 1. **Chat Interface** (💬 Tab)
- Send/receive text messages via HTTP API
- Message history stored in Zustand state
- Auto-scroll to latest message
- Loading indicators
- Error handling

### 2. **Voice Call** (🎤 Tab)
- WebSocket connection untuk real-time voice
- Audio recording menggunakan Web Audio API
- Send recorded audio to backend
- Send text messages via WebSocket
- Connection status indicator
- Processing/recording indicators

## 🔧 Components

### ChatBox Component
```tsx
<ChatBox />
```
- Text input form untuk send pesan
- Message display dengan timestamp
- Error display
- Loading state

### VoiceCallWidget Component
```tsx
<VoiceCallWidget />
```
- Start/Stop voice call button
- Real-time WebSocket connection
- Audio recording controls
- Text message input untuk voice conversation
- Response display
- Connection status indicator

## 🎛️ Hooks

### useWebSocket
Connect ke WebSocket endpoint dan handle real-time messages.

```tsx
const { isConnected, send } = useWebSocket({
  url: 'ws://localhost:8000/voice',
  onMessage: (data) => console.log(data),
  onError: (error) => console.error(error),
});

// Send message
send({ type: 'text', message: 'Hello' });
```

### useAudioRecorder
Record audio dari microphone dan convert ke base64.

```tsx
const { isRecording, startRecording, stopRecording } = useAudioRecorder({
  onAudioData: (audioBase64) => console.log(audioBase64),
  onError: (error) => console.error(error),
});

startRecording();
// ... later
stopRecording();
```

## 📦 State Management (Zustand)

```tsx
import { useConversationStore } from './store/conversationStore';

const store = useConversationStore();
// store.conversationId
// store.messages
// store.isLoading
// store.isConnected
// store.error
// store.addMessage(role, content)
```

## 🔌 API Integration

### Chat Endpoint
```
POST http://localhost:8000/chat
{
  "conversation_id": "user_123",
  "message": "Hello"
}
```

### Voice WebSocket
```
ws://localhost:8000/voice?conversation_id=user_123
```

Pesan format:
- Text: `{ type: 'text', message: '...' }`
- Audio: `{ type: 'audio', audio: 'base64_audio' }`

## 🛠️ Development Tips

### Environment Variables
Customize backend URL di `.env.local`:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Dev Server Proxy
Vite dev server proxy konfigurasi di `vite.config.ts`:
- `/api/*` → Backend API
- `/voice` → WebSocket endpoint

### TypeScript
Full TypeScript support dengan strict mode enabled.

## 🧪 Testing

```bash
# Run linter
npm run lint
```

## 📱 Browser Support
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## ⚠️ Common Issues

### WebSocket Connection Failed
- Ensure backend API running di `http://localhost:8000`
- Check `.env.local` VITE_WS_URL setting
- Browser console untuk error details

### Microphone Permission Denied
- Check browser microphone permissions
- Allow access ketika browser prompt

### CORS Errors
- Backend harus enable CORS (FastAPI CORS middleware)
- Check `CORS_ORIGINS` di backend config

## 📚 Resources

- [React Docs](https://react.dev)
- [Vite Docs](https://vite.dev)
- [Zustand Docs](https://github.com/pmndrs/zustand)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
