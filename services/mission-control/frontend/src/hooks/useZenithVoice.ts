import { useState, useCallback, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';

export function useZenithVoice(onSubmit: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);
  const [audioQueue, setAudioQueue] = useState<string[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);

  // 🎙️ [GEMINI-STREAM-SPEAK]: Bộ nhớ chunk để lọc trùng cho streaming
  const spokenChunks = useRef<Set<string>>(new Set());

  // 🏛️ [VOCAL-INTERRUPTION]: Ngắt AI ngay khi Master lên tiếng
  const cancelAI = useCallback(() => {
    window.speechSynthesis.cancel();
    setAudioQueue([]);
    setIsPlaying(false);
    spokenChunks.current.clear(); // Reset bối cảnh khi bị ngắt
  }, []);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'vi-VN';

      rec.onstart = () => {
        setIsListening(true);
        cancelAI(); // 💎 Master ưu tiên tuyệt đối
        toast.success('Zenith đang lắng nghe Master...', { id: 'voice-start', icon: '🎙️' });
      };

      rec.onresult = (event: any) => {
        const text = event.results[0][0].transcript;
        if (text) {
          onSubmit(text);
          toast.success(`Đã tiếp nhận: "${text}"`, { id: 'voice-result' });
        }
      };

      rec.onerror = (event: any) => {
        setIsListening(false);
        if (event.error !== 'no-speech') {
          toast.error('Giao thức giọng nói gặp lỗi: ' + event.error);
        }
      };

      rec.onend = () => setIsListening(false);
      setRecognition(rec);
    }
  }, [onSubmit, cancelAI]);

  // 🧠 [NEURAL-STREAM-PROCESSOR]: Xử lý hàng đợi âm thanh
  useEffect(() => {
    if (audioQueue.length > 0 && !isPlaying) {
      const nextChunk = audioQueue[0];
      setAudioQueue(prev => prev.slice(1));
      
      const synth = window.speechSynthesis;
      const utterance = new SpeechSynthesisUtterance(nextChunk);
      utterance.lang = 'vi-VN';
      utterance.rate = 1.1; // Hơi nhanh một chút để tạo cảm giác linh hoạt

      const voices = synth.getVoices();
      const premiumVoice = voices.find(v => v.lang.includes('vi') && v.name.includes('Google')) || voices.find(v => v.lang.includes('vi'));
      if (premiumVoice) utterance.voice = premiumVoice;

      utterance.onstart = () => setIsPlaying(true);
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);

      synth.speak(utterance);
    }
  }, [audioQueue, isPlaying]);

  const toggleListening = useCallback(() => {
    if (!recognition) return toast.error('Trình duyệt không hỗ trợ Voice.');
    isListening ? recognition.stop() : recognition.start();
  }, [recognition, isListening]);

  // 🎙️ [GEMINI-STREAM-SPEAK]: Đẩy chunk vào hàng đợi
  const speak = useCallback((text: string, isFinal: boolean = false) => {
    if (!text) return;
    
    // Chia nhỏ văn bản theo dấu câu
    const rawChunks = text.split(/[.,!?;:]/).filter(c => c.trim().length > 0);
    
    // Chỉ lấy những chunk mới chưa được nói (tránh lặp khi streaming)
    const newChunks: string[] = [];
    rawChunks.forEach(chunk => {
      const trimmed = chunk.trim();
      if (!spokenChunks.current.has(trimmed)) {
        newChunks.push(trimmed);
        spokenChunks.current.add(trimmed);
      }
    });

    if (newChunks.length > 0) {
      setAudioQueue(prev => [...prev, ...newChunks]);
    }

    // Nếu là kết thúc hoặc Master ngắt lời, reset bộ nhớ chunk sau khi phát xong
    if (isFinal) {
      setTimeout(() => spokenChunks.current.clear(), 1000);
    }
  }, []);

  return {
    isListening,
    isPlaying,
    toggleListening,
    speak,
    cancelAI
  };
}
