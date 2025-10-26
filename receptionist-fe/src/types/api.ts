export interface VoiceMessage {
  type: 'audio' | 'text';
  audio?: string; // base64 encoded audio
  message?: string; // text message
}

export interface VoiceResponse {
  type: 'connection' | 'response' | 'error';
  status?: 'connected';
  conversation_id?: string;
  text?: string;
  action?: 'booking' | 'transfer' | 'calendar' | 'faq' | 'response' | 'error';
  message?: string;
}

export interface ChatRequest {
  conversation_id: string;
  message: string;
}

export interface ChatResponse {
  response: string;
  action: string;
}
