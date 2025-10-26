import { useRef, useState } from 'react';

interface UseAudioPlayerOptions {
  onError?: (error: string) => void;
}

export const useAudioPlayer = ({ onError }: UseAudioPlayerOptions = {}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioBufferRef = useRef<AudioBuffer | null>(null);
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null);
  const audioChunksRef = useRef<Uint8Array[]>([]);

  // Initialize Audio Context
  const initAudioContext = () => {
    if (!audioContextRef.current) {
      try {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioContext;
      } catch (e) {
        const err = `Audio context error: ${String(e)}`;
        onError?.(err);
      }
    }
    return audioContextRef.current;
  };

  // Add audio chunk (base64 encoded PCM16)
  const addAudioChunk = (audioBase64: string) => {
    try {
      const binaryString = atob(audioBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      audioChunksRef.current.push(bytes);
    } catch (e) {
      const err = `Audio decode error: ${String(e)}`;
      onError?.(err);
    }
  };

  // Play accumulated audio
  const play = async () => {
    if (!audioChunksRef.current.length) {
      return;
    }

    const ctx = initAudioContext();
    if (!ctx) return;

    try {
      setIsPlaying(true);

      // Concatenate all chunks
      const totalLength = audioChunksRef.current.reduce((sum, chunk) => sum + chunk.length, 0);
      const concatenatedAudio = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of audioChunksRef.current) {
        concatenatedAudio.set(chunk, offset);
        offset += chunk.length;
      }

      // Convert PCM16 bytes to Float32 audio data
      const float32Audio = new Float32Array(totalLength / 2);
      const dataView = new DataView(concatenatedAudio.buffer);
      for (let i = 0; i < float32Audio.length; i++) {
        // PCM16 = signed 16-bit little-endian
        const pcm16 = dataView.getInt16(i * 2, true);
        // Normalize to -1..1
        float32Audio[i] = pcm16 / 0x8000;
      }

      // Create audio buffer
      const audioBuffer = ctx.createBuffer(
        1, // mono
        float32Audio.length,
        24000 // OpenAI Realtime uses 24kHz
      );
      audioBuffer.getChannelData(0).set(float32Audio);

      // Play
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);
      source.onended = () => {
        setIsPlaying(false);
        audioChunksRef.current = []; // Clear chunks
      };
      source.start(0);
      sourceNodeRef.current = source;
      audioBufferRef.current = audioBuffer;
    } catch (e) {
      const err = `Failed to play audio: ${String(e)}`;
      onError?.(err);
      setIsPlaying(false);
    }
  };

  // Clear chunks
  const clear = () => {
    audioChunksRef.current = [];
  };

  // Stop playback
  const stop = () => {
    if (sourceNodeRef.current) {
      try {
        sourceNodeRef.current.stop();
      } catch {
        // Already stopped
      }
    }
    setIsPlaying(false);
  };

  return {
    isPlaying,
    addAudioChunk,
    play,
    stop,
    clear,
  };
};
