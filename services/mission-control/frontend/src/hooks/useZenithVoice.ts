import { useState, useCallback, useEffect } from 'react';
import toast from 'react-hot-toast';

export function useZenithVoice(onSubmit: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'vi-VN'; // Ưu tiên tiếng Việt cho Master

      rec.onstart = () => {
        setIsListening(true);
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
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        if (event.error !== 'no-speech') {
          toast.error('Giao thức giọng nói gặp lỗi: ' + event.error);
        }
      };

      rec.onend = () => {
        setIsListening(false);
      };

      setRecognition(rec);
    }
  }, []);

  const toggleListening = useCallback(() => {
    if (!recognition) {
      toast.error('Trình duyệt của Ngài không hỗ trợ Giao thức Giọng nói.');
      return;
    }

    if (isListening) {
      recognition.stop();
    } else {
      try {
        recognition.start();
      } catch (e) {
        console.error('Recognition start failed', e);
      }
    }
  }, [recognition, isListening]);

  const speak = useCallback((text: string) => {
    const synth = window.speechSynthesis;
    if (!synth) return;

    // Ngắt các phản hồi cũ để ưu tiên cái mới
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'vi-VN';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Tìm giọng nói "Elite" nếu có (ưu tiên các giọng nam trầm ấm nếu có sẵn)
    const voices = synth.getVoices();
    const premiumVoice = voices.find(v => v.lang.includes('vi') && v.name.includes('Google')) || voices.find(v => v.lang.includes('vi'));
    if (premiumVoice) utterance.voice = premiumVoice;

    synth.speak(utterance);
  }, []);

  return { isListening, toggleListening, speak };
}
