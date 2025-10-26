import { create } from 'zustand';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ConversationState {
  conversationId: string;
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  error: string | null;

  // Actions
  setConversationId: (id: string) => void;
  addMessage: (role: 'user' | 'assistant', content: string) => void;
  setLoading: (loading: boolean) => void;
  setConnected: (connected: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  clearError: () => void;
}

export const useConversationStore = create<ConversationState>((set) => ({
  conversationId: `user_${Date.now()}`,
  messages: [],
  isLoading: false,
  isConnected: false,
  error: null,

  setConversationId: (id) => set({ conversationId: id }),

  addMessage: (role, content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `msg_${Date.now()}`,
          role,
          content,
          timestamp: new Date(),
        },
      ],
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  setConnected: (connected) => set({ isConnected: connected }),

  setError: (error) => set({ error }),

  clearMessages: () => set({ messages: [] }),

  clearError: () => set({ error: null }),
}));
