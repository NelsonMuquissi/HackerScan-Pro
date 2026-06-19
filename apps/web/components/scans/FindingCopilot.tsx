import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, User, Loader2, AlertTriangle } from 'lucide-react';
import { chatFindingCopilot } from '@/lib/api';

interface FindingCopilotProps {
  findingId: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export function FindingCopilot({ findingId }: FindingCopilotProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    setError(null);
    
    const newMessages: ChatMessage[] = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.content }));
      const response = await chatFindingCopilot(findingId, userMsg, history);
      
      setMessages([...newMessages, { role: 'assistant', content: response.reply }]);
    } catch (err: any) {
      setError(err.message || 'Erro ao comunicar com o Copilot.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[400px] bg-black/40 border border-white/10 rounded-lg overflow-hidden mt-4">
      <div className="bg-blue-500/10 border-b border-white/5 p-3 flex items-center gap-2">
        <Bot className="w-4 h-4 text-blue-400" />
        <h4 className="text-[10px] font-black text-gray-300 uppercase tracking-widest">AI Remediation Copilot</h4>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-[11px] custom-scrollbar">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 my-8">
            <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Olá! Sou o seu AI Copilot.</p>
            <p>Como posso ajudar a corrigir esta vulnerabilidade hoje?</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-blue-600/20 text-blue-400' : 'bg-emerald-600/20 text-emerald-400'}`}>
              {msg.role === 'user' ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
            </div>
            <div className={`px-3 py-2 rounded-lg max-w-[85%] whitespace-pre-wrap ${msg.role === 'user' ? 'bg-blue-500/10 border border-blue-500/20 text-blue-100' : 'bg-white/5 border border-white/10 text-gray-300'}`}>
              {msg.content}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-3">
             <div className="w-6 h-6 rounded-full bg-emerald-600/20 text-emerald-400 flex items-center justify-center shrink-0">
              <Bot className="w-3 h-3" />
            </div>
            <div className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-400 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin" /> Processando...
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center gap-2 text-neon-red bg-neon-red/10 border border-neon-red/30 p-2 rounded">
            <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}
        
        <div ref={endOfMessagesRef} />
      </div>

      <form onSubmit={handleSend} className="p-3 border-t border-white/5 bg-black/60 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pergunte algo sobre a correção..."
          className="flex-1 bg-white/5 border border-white/10 rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-blue-500 transition-colors"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-2 rounded flex items-center justify-center transition-colors disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
