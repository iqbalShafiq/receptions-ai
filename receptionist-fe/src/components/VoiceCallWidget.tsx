import { useCallback, useEffect, useState } from 'react';
import { Phone, Square } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { useConversationStore } from '../store/conversationStore';
import type { VoiceResponse } from '../types/api';
import './VoiceCallWidget.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';


export const VoiceCallWidget = () => {
  const [isCallActive, setIsCallActive] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [isPlayingResponse, setIsPlayingResponse] = useState(false);
  const { addMessage, setError } = useConversationStore();
  const audioPlayer = useAudioPlayer({
    onError: (error) => {
      setError(error);
    },
  });

  const handleVoiceMessage = useCallback((data: VoiceResponse) => {
    if (data.type === 'connection') {
      // Connected successfully
    } else if (data.type === 'response') {
      setResponseText(data.text || '');
      if (data.text) {
        addMessage('assistant', data.text);
      }
      setIsPlayingResponse(false);
    } else if (data.type === 'text_delta') {
      setResponseText(prev => prev + ((data as any).text || ''));
    } else if (data.type === 'audio_delta') {
      const audioBase64 = (data as any).audio;
      if (audioBase64) {
        audioPlayer.addAudioChunk(audioBase64);
      }
    } else if (data.type === 'response_done') {
      setIsPlayingResponse(false);
      audioPlayer.play();
    } else if (data.type === 'error') {
      setError(data.message || 'Voice call error');
      setIsPlayingResponse(false);
    }
  }, [addMessage, setError, audioPlayer]);

  const handleConnect = useCallback(() => {
    // Connected to voice service
  }, []);

  const handleDisconnect = useCallback(() => {
    setIsCallActive(false);
  }, []);

  const { isConnected, send } = useWebSocket({
    url: WS_URL + '/voice',
    onMessage: handleVoiceMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
  });

  const handleAudioData = (audioBase64: string) => {
    // Stream audio chunks in real-time to WebSocket
    if (isConnected && send) {
      send({
        type: 'audio',
        audio: audioBase64,
      });
    } else {
      setError('WebSocket not connected');
    }
  };

  const { isRecording, startRecording, stopRecording } = useAudioRecorder({
    onAudioData: handleAudioData,
    onError: (error) => {
      setError(error);
    },
  });

  const handleStartCall = async () => {
    if (!isConnected) {
      setError('Voice service not connected');
      return;
    }
    setIsCallActive(true);
    setResponseText('');
    audioPlayer.clear(); // Clear previous audio
    await startRecording();
  };

  const handleStopCall = () => {
    stopRecording();
    setIsCallActive(false);
    setIsPlayingResponse(false);
  };

  const handleSendText = (text: string) => {
    if (isConnected && send && text.trim()) {
      send({
        type: 'text',
        message: text,
      });
      addMessage('user', text);
      setIsPlayingResponse(true);
    }
  };

  return (
    <div className="voice-widget">
      <div className="voice-header">
        <h3>Voice Call</h3>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          <span className="status-dot"></span>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <div className="voice-content">
        {responseText && (
          <div className="response-box">
            <p>{responseText}</p>
          </div>
        )}

        <div className="voice-controls">
          <div className="voice-button-container">
            {!isCallActive ? (
              <button
                onClick={handleStartCall}
                disabled={!isConnected}
                className="mic-button"
                title="Start Voice Call"
              >
                <Phone size={32} />
              </button>
            ) : (
              <button onClick={handleStopCall} className="mic-button recording" title="Stop Recording">
                <Square size={32} />
              </button>
            )}
            {!isCallActive && <p className="button-label">Click to call the receptionist</p>}
          </div>
        </div>

        {isRecording && (
          <div className="recording-indicator">
            <span className="pulse"></span>
            Recording...
          </div>
        )}

        {isPlayingResponse && (
          <div className="processing-indicator">
            <span className="spinner"></span>
            Processing response...
          </div>
        )}
      </div>
    </div>
  );
};
