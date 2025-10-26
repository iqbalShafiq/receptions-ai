import { useEffect, useRef, useState } from 'react';

interface UseAudioRecorderOptions {
  onAudioData?: (audioBase64: string) => void;
  onError?: (error: string) => void;
}

/**
 * Hook for recording audio as PCM16 and streaming it in real-time
 * Compatible with OpenAI Realtime API (24kHz, PCM16, mono)
 */
export const useAudioRecorder = ({ onAudioData, onError }: UseAudioRecorderOptions = {}) => {
  const [isRecording, setIsRecording] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);

  const startRecording = async () => {
    try {
      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1, // Mono
          sampleRate: 24000, // Try to get 24kHz directly
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      streamRef.current = stream;

      // Create audio context with 24kHz sample rate (OpenAI Realtime API requirement)
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 24000,
      });
      audioContextRef.current = audioContext;

      // Create source from microphone stream
      const source = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // Create processor node for capturing raw audio
      // Buffer size: 4096 samples = ~170ms chunks at 24kHz
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorNodeRef.current = processor;

      // Set recording state BEFORE connecting to avoid race condition
      setIsRecording(true);

      processor.onaudioprocess = (event) => {
        // Get raw audio samples (Float32Array, range -1 to 1)
        const inputData = event.inputBuffer.getChannelData(0);

        // Convert Float32 to PCM16 (16-bit signed integer)
        const pcm16Data = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          // Clamp to -1..1 and convert to -32768..32767
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // Convert to base64
        const bytes = new Uint8Array(pcm16Data.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64Audio = btoa(binary);

        // Send audio chunk immediately (real-time streaming)
        onAudioData?.(base64Audio);
      };

      // Connect: microphone -> processor -> destination
      source.connect(processor);
      processor.connect(audioContext.destination);
    } catch (e) {
      const errorMsg = `Failed to start recording: ${String(e)}`;
      console.error(errorMsg);
      onError?.(errorMsg);
    }
  };

  const stopRecording = () => {
    if (!isRecording) return;

    setIsRecording(false);

    // Disconnect and cleanup audio nodes
    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }

    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop microphone stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      stopRecording();
    };
  }, []);

  return { isRecording, startRecording, stopRecording };
};
